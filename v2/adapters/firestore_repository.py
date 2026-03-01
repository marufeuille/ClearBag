"""Firestore Repository Adapter

DocumentRepository, UserConfigRepository, FamilyRepository の Firestore 実装。

Firestore コレクション構造:
  families/{familyId}                              ← ファミリー設定
  families/{familyId}/members/{uid}                ← メンバー
  families/{familyId}/invitations/{invitationId}   ← 招待
  families/{familyId}/profiles/{profileId}         ← プロファイル（子ども情報）
  families/{familyId}/documents/{documentId}       ← ドキュメントレコード
  families/{familyId}/documents/{docId}/events/    ← 非正規化イベント（日付範囲クエリ用）
  families/{familyId}/documents/{docId}/tasks/     ← 非正規化タスク

  users/{uid}                                      ← ユーザー個人設定
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
from v2.domain.ports import DocumentRepository, FamilyRepository, UserConfigRepository


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

_FAMILIES = "families"
_MEMBERS = "members"
_INVITATIONS = "invitations"
_PROFILES = "profiles"
_DOCUMENTS = "documents"
_EVENTS = "events"
_TASKS = "tasks"
_USERS = "users"


class FirestoreDocumentRepository(DocumentRepository):
    """
    Firestore を使った DocumentRepository 実装。

    families/{familyId}/documents, events, tasks の各サブコレクションを管理する。
    """

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    # ── DocumentRecord CRUD ──────────────────────────────────────────────────

    def create(self, uid: str, record: DocumentRecord) -> str:
        """ドキュメントレコードを Firestore に作成。IDを返す"""
        doc_id = record.id or str(uuid.uuid4())
        ref = (
            self._db.collection(_FAMILIES)
            .document(uid)
            .collection(_DOCUMENTS)
            .document(doc_id)
        )
        ref.set(self._record_to_dict(record))
        logger.info("Created document: family_id=%s, doc_id=%s", uid, doc_id)
        return doc_id

    def get(self, uid: str, document_id: str) -> DocumentRecord | None:
        """ドキュメントレコードを取得。存在しない場合は None を返す"""
        snap = (
            self._db.collection(_FAMILIES)
            .document(uid)
            .collection(_DOCUMENTS)
            .document(document_id)
            .get()
        )
        if not snap.exists:
            return None
        return self._dict_to_record(document_id, uid, snap.to_dict())

    def list(self, uid: str) -> list[DocumentRecord]:
        """ファミリーのドキュメント一覧を新しい順で取得"""
        snaps = (
            self._db.collection(_FAMILIES)
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
            self._db.collection(_FAMILIES)
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
            "Updated status: family_id=%s, doc_id=%s, status=%s",
            uid,
            document_id,
            status,
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
            self._db.collection(_FAMILIES)
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
                "archive_filename": analysis.archive_filename,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )

        # events サブコレクションに保存
        # family_id は collection_group クエリのフィルター用（必須）
        events_col = doc_ref.collection(_EVENTS)
        for event in analysis.events:
            event_ref = events_col.document()
            batch.set(
                event_ref,
                {
                    "family_id": uid,
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
        # family_id は collection_group クエリのフィルター用（必須）
        tasks_col = doc_ref.collection(_TASKS)
        for task in analysis.tasks:
            task_ref = tasks_col.document()
            batch.set(
                task_ref,
                {
                    "family_id": uid,
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
            "Saved analysis: family_id=%s, doc_id=%s, events=%d, tasks=%d",
            uid,
            document_id,
            len(analysis.events),
            len(analysis.tasks),
        )

    def delete(self, uid: str, document_id: str) -> None:
        """ドキュメントと関連する events/tasks を削除"""
        doc_ref = (
            self._db.collection(_FAMILIES)
            .document(uid)
            .collection(_DOCUMENTS)
            .document(document_id)
        )
        # サブコレクションを先に削除
        for sub in (doc_ref.collection(_EVENTS), doc_ref.collection(_TASKS)):
            for snap in sub.stream():
                snap.reference.delete()
        doc_ref.delete()
        logger.info("Deleted document: family_id=%s, doc_id=%s", uid, document_id)

    def find_by_content_hash(
        self, uid: str, content_hash: str
    ) -> DocumentRecord | None:
        """コンテンツハッシュで検索（冪等性チェック）"""
        snaps = (
            self._db.collection(_FAMILIES)
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
        # order_by("start") により複合 COLLECTION_GROUP インデックス (family_id, start) を使用
        query = (
            self._db.collection_group(_EVENTS)
            .where("family_id", "==", uid)
            .order_by("start")
        )
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
        # order_by("completed") により複合 COLLECTION_GROUP インデックス (family_id, completed) を使用
        query = (
            self._db.collection_group(_TASKS)
            .where("family_id", "==", uid)
            .order_by("completed")
        )
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
        snaps = self._db.collection_group(_TASKS).where("family_id", "==", uid).stream()
        for snap in snaps:
            if snap.id == task_id:
                snap.reference.update({"completed": completed})
                logger.info(
                    "Updated task: family_id=%s, task_id=%s, completed=%s",
                    uid,
                    task_id,
                    completed,
                )
                return
        logger.warning("Task not found: family_id=%s, task_id=%s", uid, task_id)

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
            "archive_filename": record.archive_filename,
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
            archive_filename=data.get("archive_filename", ""),
            error_message=data.get("error_message"),
        )


class FirestoreUserConfigRepository(UserConfigRepository):
    """
    Firestore を使った UserConfigRepository 実装。

    users/{uid} の個人設定（ical_token, notification_preferences）のみを管理する。
    ファミリー共有データ（profiles, plan等）は FirestoreFamilyRepository を使用。
    """

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def get_user(self, uid: str) -> dict:
        """ユーザー設定を取得。存在しない場合は空のデフォルト設定を返す"""
        snap = self._db.collection(_USERS).document(uid).get()
        if not snap.exists:
            return {
                "ical_token": str(uuid.uuid4()),
            }
        return snap.to_dict() or {}

    def update_user(self, uid: str, data: dict) -> None:
        """ユーザー設定を更新（部分更新）

        dot-notation キー（例: "notification_preferences.email"）が含まれる場合は
        update() を使用してネストフィールドを部分更新する。
        set(merge=True) は dot-notation を文字通りのフィールド名として扱うため不可。
        top-level キーのみの場合は set(merge=True) でドキュメント新規作成も兼ねる。
        """
        doc_ref = self._db.collection(_USERS).document(uid)
        if any("." in key for key in data):
            # update() はドキュメントが存在する前提だが、update_user の呼び出し元は
            # 常に get_family_context 経由でドキュメントが作成済みのフロー
            doc_ref.update(data)
        else:
            doc_ref.set(data, merge=True)
        logger.info("Updated user settings: uid=%s", uid)


class FirestoreFamilyRepository(FamilyRepository):
    """
    Firestore を使った FamilyRepository 実装。

    families/{familyId}, members, invitations, profiles を管理する。
    """

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    # ── ファミリー CRUD ────────────────────────────────────────────────────────

    def create_family(self, family_id: str, owner_uid: str, name: str) -> None:
        """ファミリーを作成"""
        self._db.collection(_FAMILIES).document(family_id).set(
            {
                "owner_uid": owner_uid,
                "name": name,
                "plan": "free",
                "documents_this_month": 0,
                "last_reset_at": firestore.SERVER_TIMESTAMP,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )
        logger.info("Created family: family_id=%s, owner=%s", family_id, owner_uid)

    def get_family(self, family_id: str) -> dict | None:
        """ファミリー設定を取得"""
        snap = self._db.collection(_FAMILIES).document(family_id).get()
        if not snap.exists:
            return None
        return snap.to_dict() or {}

    def update_family(self, family_id: str, data: dict) -> None:
        """ファミリー設定を更新（部分更新）"""
        data["updated_at"] = firestore.SERVER_TIMESTAMP
        self._db.collection(_FAMILIES).document(family_id).set(data, merge=True)
        logger.info("Updated family: family_id=%s", family_id)

    # ── メンバー管理 ──────────────────────────────────────────────────────────

    def add_member(
        self, family_id: str, uid: str, role: str, display_name: str, email: str
    ) -> None:
        """ファミリーにメンバーを追加"""
        self._db.collection(_FAMILIES).document(family_id).collection(
            _MEMBERS
        ).document(uid).set(
            {
                "role": role,
                "display_name": display_name,
                "email": email,
                "joined_at": firestore.SERVER_TIMESTAMP,
            }
        )
        logger.info("Added member: family_id=%s, uid=%s, role=%s", family_id, uid, role)

    def update_member(self, family_id: str, uid: str, updates: dict) -> None:
        """メンバーの属性を部分更新"""
        self._db.collection(_FAMILIES).document(family_id).collection(
            _MEMBERS
        ).document(uid).update(updates)

    def remove_member(self, family_id: str, uid: str) -> None:
        """ファミリーからメンバーを削除"""
        self._db.collection(_FAMILIES).document(family_id).collection(
            _MEMBERS
        ).document(uid).delete()
        logger.info("Removed member: family_id=%s, uid=%s", family_id, uid)

    def list_members(self, family_id: str) -> list[dict]:
        """メンバー一覧を取得"""
        snaps = (
            self._db.collection(_FAMILIES)
            .document(family_id)
            .collection(_MEMBERS)
            .stream()
        )
        return [{"uid": snap.id, **(snap.to_dict() or {})} for snap in snaps]

    def get_member(self, family_id: str, uid: str) -> dict | None:
        """メンバーの全データを取得。未参加の場合はNoneを返す"""
        snap = (
            self._db.collection(_FAMILIES)
            .document(family_id)
            .collection(_MEMBERS)
            .document(uid)
            .get()
        )
        if not snap.exists:
            return None
        return snap.to_dict() or {}

    def get_member_role(self, family_id: str, uid: str) -> str | None:
        """メンバーのロールを取得。未参加の場合はNoneを返す"""
        member = self.get_member(family_id, uid)
        if member is None:
            return None
        return member.get("role")

    # ── 招待管理 ──────────────────────────────────────────────────────────────

    def create_invitation(
        self, family_id: str, email: str, invited_by_uid: str, token: str
    ) -> str:
        """招待を作成。生成されたIDを返す"""
        import datetime

        ref = (
            self._db.collection(_FAMILIES)
            .document(family_id)
            .collection(_INVITATIONS)
            .document()
        )
        expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=7)
        ref.set(
            {
                "email": email,
                "invited_by_uid": invited_by_uid,
                "token": token,
                "status": "pending",
                "family_id": family_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "expires_at": expires_at,
            }
        )
        logger.info("Created invitation: family_id=%s, email=%s", family_id, email)
        return ref.id

    def get_invitation_by_token(self, token: str) -> dict | None:
        """招待トークンで招待情報を取得"""
        snaps = (
            self._db.collection_group(_INVITATIONS)
            .where("token", "==", token)
            .limit(1)
            .stream()
        )
        for snap in snaps:
            return {"id": snap.id, **(snap.to_dict() or {})}
        return None

    def accept_invitation(self, invitation_id: str, family_id: str) -> None:
        """招待ステータスを accepted に更新"""
        self._db.collection(_FAMILIES).document(family_id).collection(
            _INVITATIONS
        ).document(invitation_id).update({"status": "accepted"})
        logger.info(
            "Accepted invitation: family_id=%s, invitation_id=%s",
            family_id,
            invitation_id,
        )

    # ── プロファイル管理 ──────────────────────────────────────────────────────

    def list_profiles(self, family_id: str) -> list[UserProfile]:
        """プロファイル一覧を取得"""
        snaps = (
            self._db.collection(_FAMILIES)
            .document(family_id)
            .collection(_PROFILES)
            .stream()
        )
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

    def create_profile(self, family_id: str, profile: UserProfile) -> str:
        """プロファイルを作成。生成されたIDを返す"""
        col = self._db.collection(_FAMILIES).document(family_id).collection(_PROFILES)
        ref = col.add(
            {
                "name": profile.name,
                "grade": profile.grade,
                "keywords": profile.keywords,
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )[1]
        logger.info("Created profile: family_id=%s, profile_id=%s", family_id, ref.id)
        return ref.id

    def update_profile(
        self, family_id: str, profile_id: str, profile: UserProfile
    ) -> None:
        """プロファイルを更新"""
        self._db.collection(_FAMILIES).document(family_id).collection(
            _PROFILES
        ).document(profile_id).update(
            {
                "name": profile.name,
                "grade": profile.grade,
                "keywords": profile.keywords,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )
        logger.info(
            "Updated profile: family_id=%s, profile_id=%s", family_id, profile_id
        )

    def delete_profile(self, family_id: str, profile_id: str) -> None:
        """プロファイルを削除"""
        self._db.collection(_FAMILIES).document(family_id).collection(
            _PROFILES
        ).document(profile_id).delete()
        logger.info(
            "Deleted profile: family_id=%s, profile_id=%s", family_id, profile_id
        )
