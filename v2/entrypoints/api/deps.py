"""FastAPI 依存性注入

Firebase Auth JWT 検証と Firestore リポジトリの初期化を担当する。
各ルートは Depends() でこのモジュールの関数を呼び出して認証 uid と
リポジトリインスタンスを受け取る。
"""

from __future__ import annotations

import logging
import os

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
    FirestoreUserConfigRepository,
)
from v2.adapters.ical_renderer import ICalRenderer

logger = logging.getLogger(__name__)

# ── Firebase Admin 初期化（プロセス内で1回のみ） ────────────────────────────────

_firebase_app: firebase_admin.App | None = None


def _get_firebase_app() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is None:
        # Cloud Run 環境では Application Default Credentials を使用
        cred = fb_creds.ApplicationDefault()
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialized")
    return _firebase_app


# ── 認証 ────────────────────────────────────────────────────────────────────────

_bearer = HTTPBearer()


async def get_current_uid(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """
    Authorization: Bearer <id_token> ヘッダーを検証して uid を返す。

    Returns:
        Firebase Auth の uid（例: "abc123xyz"）

    Raises:
        HTTPException(401): トークンが無効な場合
    """
    _get_firebase_app()
    try:
        decoded = fb_auth.verify_id_token(creds.credentials)
        return decoded["uid"]
    except Exception as e:
        logger.warning("Invalid Firebase ID token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token",
        ) from e


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


def get_blob_storage() -> GCSBlobStorage:
    """BlobStorage を返す依存関数"""
    bucket = os.environ["GCS_BUCKET_NAME"]
    return GCSBlobStorage(bucket_name=bucket)


def get_task_queue() -> CloudTasksQueue:
    """TaskQueue を返す依存関数"""
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
