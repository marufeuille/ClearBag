"""Firestore Repository Adapter

DocumentRepository と UserConfigRepository の Firestore 実装。

Firestore コレクション構造:
  users/{uid}                               ← ユーザー設定
  users/{uid}/profiles/{profileId}          ← プロファイル
  users/{uid}/documents/{documentId}        ← ドキュメントレコード
  users/{uid}/events/{eventId}              ← 非正規化イベント（日付範囲クエリ用）
  users/{uid}/tasks/{taskId}                ← 非正規化タスク
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from google.cloud import firestore

from v2.domain.models import (
    DocumentAnalysis,
    DocumentRecord,
    EventData,
    UserProfile,
)
from v2.domain.ports import DocumentRepository, UserConfigRepository


@dataclass
class StoredTaskData:
    """Firestore に永続化されたタスク（id と completed を含む）"""

    id: str
    title: str
    due_date: str
    assignee: str
    note: str
    completed: bool


logger = logging.getLogger(__name__)

_USERS = "users"
_PROFILES = "profiles"
_DOCUMENTS = "documents"
_EVENTS = "events"
_TASKS = "tasks"


class FirestoreDocumentRepository(DocumentRepository):
    """
    Firestore を使った DocumentRepository 実装。

    users/{uid}/documents, events, tasks の各サブコレクションを管理する。
    """

    def __init__(self, db: firestore.Client) -> None:
        """
        Args:
            db: 初期化済みの Firestore クライアント
        """
        self._db = db

    # ── DocumentRecord CRUD ──────────────────────────────────────────────────

    def create(self, uid: str, record: DocumentRecord) -> str:
        """ドキュメントレコードを Firestore に作成。IDを返す"""
        doc_id = record.id or str(uuid.uuid4())
        ref = (
            self._db.collection(_USERS)
            .document(uid)
            .collection(_DOCUMENTS)
            .document(doc_id)
        )
        ref.set(self._record_to_dict(record))
        logger.info("Created document: uid=%s, doc_id=%s", uid, doc_id)
        return doc_id

    def get(self, uid: str, document_id: str) -> DocumentRecord | None:
        """ドキュメントレコードを取得。存在しない場合は None を返す"""
        snap = (
            self._db.collection(_USERS)
            .document(uid)
            .collection(_DOCUMENTS)
            .document(document_id)
            .get()
        )
        if not snap.exists:
            return None
        return self._dict_to_record(document_id, uid, snap.to_dict())

    def list(self, uid: str) -> list[DocumentRecord]:
        """ユーザーのドキュメント一覧を新しい順で取得"""
        snaps = (
            self._db.collection(_USERS)
            .document(uid)
            .collection(_DOCUMENTS)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        return [self._dict_to_record(snap.id, uid, snap.to_dict()) for snap in snaps]

    def update_status(
        self,
        uid: str,
        document_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """ドキュメントのステータスを更新"""
        ref = (
            self._db.collection(_USERS)
            .document(uid)
            .collection(_DOCUMENTS)
            .document(document_id)
        )
        update: dict[str, Any] = {
            "status": status,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        if error_message is not None:
            update["error_message"] = error_message
        ref.update(update)
        logger.info(
            "Updated status: uid=%s, doc_id=%s, status=%s", uid, document_id, status
        )

    def save_analysis(
        self, uid: str, document_id: str, analysis: DocumentAnalysis
    ) -> None:
        """
        解析結果を Firestore に保存。

        - documents/{documentId} の summary/category を更新
        - events サブコレクションに EventData を書き込み
        - tasks サブコレクションに TaskData を書き込み
        """
        doc_ref = (
            self._db.collection(_USERS)
            .document(uid)
            .collection(_DOCUMENTS)
            .document(document_id)
        )

        # バッチ書き込み
        batch = self._db.batch()

        # ドキュメント本体を更新
        batch.update(
            doc_ref,
            {
                "status": "completed",
                "summary": analysis.summary,
                "category": analysis.category.value,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )

        # events サブコレクションに保存
        # user_uid は collection_group クエリのフィルター用（必須）
        events_col = doc_ref.collection(_EVENTS)
        for event in analysis.events:
            event_ref = events_col.document()
            batch.set(
                event_ref,
                {
                    "user_uid": uid,
                    "document_id": document_id,
                    "summary": event.summary,
                    "start": event.start,
                    "end": event.end,
                    "location": event.location,
                    "description": event.description,
                    "confidence": event.confidence,
                },
            )

        # tasks サブコレクションに保存
        # user_uid は collection_group クエリのフィルター用（必須）
        tasks_col = doc_ref.collection(_TASKS)
        for task in analysis.tasks:
            task_ref = tasks_col.document()
            batch.set(
                task_ref,
                {
                    "user_uid": uid,
                    "document_id": document_id,
                    "title": task.title,
                    "due_date": task.due_date,
                    "assignee": task.assignee,
                    "note": task.note,
                    "completed": False,
                },
            )

        batch.commit()
        logger.info(
            "Saved analysis: uid=%s, doc_id=%s, events=%d, tasks=%d",
            uid,
            document_id,
            len(analysis.events),
            len(analysis.tasks),
        )

    def delete(self, uid: str, document_id: str) -> None:
        """ドキュメントと関連する events/tasks を削除"""
        doc_ref = (
            self._db.collection(_USERS)
            .document(uid)
            .collection(_DOCUMENTS)
            .document(document_id)
        )
        # サブコレクションを先に削除
        for sub in (doc_ref.collection(_EVENTS), doc_ref.collection(_TASKS)):
            for snap in sub.stream():
                snap.reference.delete()
        doc_ref.delete()
        logger.info("Deleted document: uid=%s, doc_id=%s", uid, document_id)

    def find_by_content_hash(
        self, uid: str, content_hash: str
    ) -> DocumentRecord | None:
        """コンテンツハッシュで検索（冪等性チェック）"""
        snaps = (
            self._db.collection(_USERS)
            .document(uid)
            .collection(_DOCUMENTS)
            .where("content_hash", "==", content_hash)
            .limit(1)
            .stream()
        )
        for snap in snaps:
            return self._dict_to_record(snap.id, uid, snap.to_dict())
        return None

    # ── イベント・タスク クエリ ─────────────────────────────────────────────

    def list_events(
        self,
        uid: str,
        from_date: str | None = None,
        to_date: str | None = None,
        profile_id: str | None = None,
    ) -> list[EventData]:
        """日付範囲でイベントを取得（全ドキュメントをまたいだビュー）"""
        # documents/{id}/events をコレクショングループクエリで横断検索
        query = self._db.collection_group(_EVENTS).where("user_uid", "==", uid)
        if from_date:
            query = query.where("start", ">=", from_date)
        if to_date:
            query = query.where("start", "<=", to_date + "T23:59:59")

        return [
            EventData(
                summary=d.get("summary", ""),
                start=d.get("start", ""),
                end=d.get("end", ""),
                location=d.get("location", ""),
                description=d.get("description", ""),
                confidence=d.get("confidence", "HIGH"),
            )
            for snap in query.stream()
            for d in (snap.to_dict() or {},)
        ]

    def list_tasks(
        self, uid: str, completed: bool | None = None
    ) -> list[StoredTaskData]:
        """タスク一覧を取得（id・completed を含む）"""
        query = self._db.collection_group(_TASKS).where("user_uid", "==", uid)
        if completed is not None:
            query = query.where("completed", "==", completed)

        return [
            StoredTaskData(
                id=snap.id,
                title=d.get("title", ""),
                due_date=d.get("due_date", ""),
                assignee=d.get("assignee", "PARENT"),
                note=d.get("note", ""),
                completed=d.get("completed", False),
            )
            for snap in query.stream()
            for d in (snap.to_dict() or {},)
        ]

    def update_task_completed(self, uid: str, task_id: str, completed: bool) -> None:
        """タスクの完了状態を更新"""
        # tasks コレクショングループから task_id を探してアップデート
        snaps = self._db.collection_group(_TASKS).where("user_uid", "==", uid).stream()
        for snap in snaps:
            if snap.id == task_id:
                snap.reference.update({"completed": completed})
                logger.info(
                    "Updated task: uid=%s, task_id=%s, completed=%s",
                    uid,
                    task_id,
                    completed,
                )
                return
        logger.warning("Task not found: uid=%s, task_id=%s", uid, task_id)

    # ── 変換ヘルパー ──────────────────────────────────────────────────────────

    @staticmethod
    def _record_to_dict(record: DocumentRecord) -> dict:
        return {
            "uid": record.uid,
            "status": record.status,
            "content_hash": record.content_hash,
            "storage_path": record.storage_path,
            "original_filename": record.original_filename,
            "mime_type": record.mime_type,
            "summary": record.summary,
            "category": record.category,
            "error_message": record.error_message,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

    @staticmethod
    def _dict_to_record(doc_id: str, uid: str, data: dict) -> DocumentRecord:
        return DocumentRecord(
            id=doc_id,
            uid=uid,
            status=data.get("status", "pending"),
            content_hash=data.get("content_hash", ""),
            storage_path=data.get("storage_path", ""),
            original_filename=data.get("original_filename", ""),
            mime_type=data.get("mime_type", "application/octet-stream"),
            summary=data.get("summary", ""),
            category=data.get("category", ""),
            error_message=data.get("error_message"),
        )


class FirestoreUserConfigRepository(UserConfigRepository):
    """
    Firestore を使った UserConfigRepository 実装。

    users/{uid} と users/{uid}/profiles/{profileId} を管理する。
    """

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def get_user(self, uid: str) -> dict:
        """ユーザー設定を取得。存在しない場合は空のデフォルト設定を返す"""
        snap = self._db.collection(_USERS).document(uid).get()
        if not snap.exists:
            return {
                "plan": "free",
                "documents_this_month": 0,
                "ical_token": str(uuid.uuid4()),
            }
        return snap.to_dict() or {}

    def update_user(self, uid: str, data: dict) -> None:
        """ユーザー設定を更新（部分更新）"""
        self._db.collection(_USERS).document(uid).set(data, merge=True)
        logger.info("Updated user settings: uid=%s", uid)

    def list_profiles(self, uid: str) -> list[UserProfile]:
        """プロファイル一覧を取得"""
        snaps = self._db.collection(_USERS).document(uid).collection(_PROFILES).stream()
        return [
            UserProfile(
                id=snap.id,
                name=d.get("name", ""),
                grade=d.get("grade", ""),
                keywords=d.get("keywords", ""),
            )
            for snap in snaps
            for d in (snap.to_dict() or {},)
        ]

    def create_profile(self, uid: str, profile: UserProfile) -> str:
        """プロファイルを作成。生成されたIDを返す"""
        col = self._db.collection(_USERS).document(uid).collection(_PROFILES)
        ref = col.add(
            {
                "name": profile.name,
                "grade": profile.grade,
                "keywords": profile.keywords,
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )[1]
        logger.info("Created profile: uid=%s, profile_id=%s", uid, ref.id)
        return ref.id

    def update_profile(self, uid: str, profile_id: str, profile: UserProfile) -> None:
        """プロファイルを更新"""
        self._db.collection(_USERS).document(uid).collection(_PROFILES).document(
            profile_id
        ).update(
            {
                "name": profile.name,
                "grade": profile.grade,
                "keywords": profile.keywords,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )
        logger.info("Updated profile: uid=%s, profile_id=%s", uid, profile_id)

    def delete_profile(self, uid: str, profile_id: str) -> None:
        """プロファイルを削除"""
        self._db.collection(_USERS).document(uid).collection(_PROFILES).document(
            profile_id
        ).delete()
        logger.info("Deleted profile: uid=%s, profile_id=%s", uid, profile_id)
