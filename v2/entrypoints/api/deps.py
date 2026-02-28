"""FastAPI 依存性注入

Firebase Auth JWT 検証と Firestore リポジトリの初期化を担当する。
各ルートは Depends() でこのモジュールの関数を呼び出して認証 uid と
リポジトリインスタンスを受け取る。
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass

import firebase_admin
import firebase_admin.auth as fb_auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import credentials as fb_creds
from google.cloud import firestore

from v2.adapters.cloud_storage import GCSBlobStorage
from v2.adapters.cloud_tasks_queue import CloudTasksQueue
from v2.adapters.firestore_repository import (
    FirestoreDocumentRepository,
    FirestoreFamilyRepository,
    FirestoreUserConfigRepository,
)
from v2.adapters.ical_renderer import ICalRenderer

logger = logging.getLogger(__name__)

# ── Firebase Admin 初期化（プロセス内で1回のみ） ────────────────────────────────

_firebase_app: firebase_admin.App | None = None


def _get_firebase_app() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is None:
        try:
            # 既に初期化済み（worker などが先に初期化した場合）
            _firebase_app = firebase_admin.get_app()
        except ValueError:
            cred = fb_creds.ApplicationDefault()
            # PROJECT_ID で Firebase Auth / Firestore の両方を初期化
            project_id = os.environ.get("PROJECT_ID")
            _firebase_app = firebase_admin.initialize_app(
                cred,
                options={"projectId": project_id} if project_id else {},
            )
            logger.info("Firebase Admin initialized (deps) project=%s", project_id)
    return _firebase_app


# ── 認証 ────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AuthInfo:
    """Firebase Auth JWT から取得した認証情報"""

    uid: str
    email: str
    display_name: str


_bearer = HTTPBearer()


async def get_auth_info(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthInfo:
    """
    Authorization: Bearer <id_token> ヘッダーを検証して AuthInfo を返す。

    Returns:
        AuthInfo（uid, email, display_name）

    Raises:
        HTTPException(401): トークンが無効な場合
    """
    _get_firebase_app()
    try:
        decoded = fb_auth.verify_id_token(creds.credentials)
    except Exception as e:
        logger.warning("Invalid Firebase ID token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token",
        ) from e

    return AuthInfo(
        uid=decoded["uid"],
        email=decoded.get("email", ""),
        display_name=decoded.get("name", ""),
    )


async def get_current_uid(
    auth_info: AuthInfo = Depends(get_auth_info),
) -> str:
    """
    get_auth_info() の後方互換ラッパー。uid のみを返す。
    既存のルートが Depends(get_current_uid) で uid を取得している場合に使用。
    """
    return auth_info.uid


# ── ファミリーコンテキスト ────────────────────────────────────────────────────


@dataclass(frozen=True)
class FamilyContext:
    """認証済みユーザーのファミリーコンテキスト"""

    uid: str
    family_id: str
    role: str  # "owner" | "member"


async def get_family_context(
    auth_info: AuthInfo = Depends(get_auth_info),
) -> FamilyContext:
    """
    uid からファミリーコンテキストを解決する。

    users/{uid} に family_id が未設定の場合、自動的に1人ファミリーを作成する。
    また users/{uid} に email/display_name が未設定の場合、JWT claims から同期する。

    Returns:
        FamilyContext（uid, family_id, role）
    """
    uid = auth_info.uid
    db = _get_firestore_client()
    user_repo = FirestoreUserConfigRepository(db)
    family_repo = FirestoreFamilyRepository(db)

    user_data = user_repo.get_user(uid)

    # ── アクティベーションチェック ──────────────────────────────────────────
    # is_activated: True のユーザーのみサービスを利用できる。
    # アクティベーション方法:
    #   1. 招待リンク経由の join (POST /api/families/join)
    #   2. Firestore Console から users/{uid}/is_activated を true に設定
    #   3. scripts/activate_existing_users.py で一括設定
    if not user_data.get("is_activated", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ACTIVATION_REQUIRED",
        )

    family_id = user_data.get("family_id")

    # JWT から display_name/email を同期（空の場合のみ）
    updates: dict = {}
    if not user_data.get("email") and auth_info.email:
        updates["email"] = auth_info.email
    if not user_data.get("display_name") and auth_info.display_name:
        updates["display_name"] = auth_info.display_name
    if updates:
        user_repo.update_user(uid, updates)
        user_data = {**user_data, **updates}

    if not family_id:
        # 初回アクセス時: 1人ファミリーを自動作成
        family_id = str(uuid.uuid4())
        email = user_data.get("email", auth_info.email)
        display_name = user_data.get(
            "display_name", auth_info.display_name or email or uid
        )

        family_repo.create_family(
            family_id=family_id,
            owner_uid=uid,
            name="マイファミリー",
        )
        family_repo.add_member(
            family_id=family_id,
            uid=uid,
            role="owner",
            display_name=display_name,
            email=email,
        )
        user_repo.update_user(uid, {"family_id": family_id})
        logger.info("Auto-created family: uid=%s, family_id=%s", uid, family_id)

    member_data = family_repo.get_member(family_id, uid)
    role = (member_data or {}).get("role") or "member"

    # member エントリの email/display_name が空なら user_data の値で補完
    # users/{uid} が先に同期済みでも member エントリが空のケースをカバー
    if member_data:
        email = user_data.get("email", "")
        display_name = user_data.get("display_name", "")
        member_updates: dict = {}
        if not member_data.get("email") and email:
            member_updates["email"] = email
        if not member_data.get("display_name") and display_name:
            member_updates["display_name"] = display_name
        if member_updates:
            family_repo.update_member(family_id, uid, member_updates)

    return FamilyContext(uid=uid, family_id=family_id, role=role)


async def require_owner(
    ctx: FamilyContext = Depends(get_family_context),
) -> FamilyContext:
    """
    オーナー権限を要求する依存関数。

    Raises:
        HTTPException(403): ロールが "owner" でない場合
    """
    if ctx.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作にはオーナー権限が必要です。",
        )
    return ctx


# ── Firestore クライアント（シングルトン） ──────────────────────────────────────

_firestore_client: firestore.Client | None = None


def _get_firestore_client() -> firestore.Client:
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client()
        logger.info("Firestore client initialized")
    return _firestore_client


# ── リポジトリ依存 ─────────────────────────────────────────────────────────────


def get_document_repo() -> FirestoreDocumentRepository:
    """DocumentRepository を返す依存関数"""
    return FirestoreDocumentRepository(_get_firestore_client())


def get_user_config_repo() -> FirestoreUserConfigRepository:
    """UserConfigRepository を返す依存関数"""
    return FirestoreUserConfigRepository(_get_firestore_client())


def get_family_repo() -> FirestoreFamilyRepository:
    """FamilyRepository を返す依存関数"""
    return FirestoreFamilyRepository(_get_firestore_client())


def get_blob_storage() -> GCSBlobStorage:
    """BlobStorage を返す依存関数"""
    bucket = os.environ["GCS_BUCKET_NAME"]
    return GCSBlobStorage(bucket_name=bucket)


def get_task_queue() -> CloudTasksQueue | None:
    """
    TaskQueue を返す依存関数。

    LOCAL_MODE=true の場合は None を返す（BackgroundTasks で代替）。
    """
    if os.environ.get("LOCAL_MODE"):
        return None  # type: ignore[return-value]
    return CloudTasksQueue(
        project_id=os.environ["PROJECT_ID"],
        location=os.environ.get("CLOUD_TASKS_LOCATION", "asia-northeast1"),
        queue_name=os.environ["CLOUD_TASKS_QUEUE"],
        worker_url=os.environ["WORKER_URL"],
        service_account_email=os.environ["SERVICE_ACCOUNT_EMAIL"],
    )


def get_ical_renderer() -> ICalRenderer:
    """CalendarFeedRenderer を返す依存関数"""
    return ICalRenderer()
