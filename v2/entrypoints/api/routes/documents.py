"""ドキュメント API ルート

POST /api/documents/upload  → 202 { id, status }
GET  /api/documents          → 200 [DocumentRecord...]
GET  /api/documents/{id}     → 200 DocumentRecord
DELETE /api/documents/{id}   → 204
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel

from v2.adapters.cloud_storage import GCSBlobStorage
from v2.adapters.cloud_tasks_queue import CloudTasksQueue
from v2.adapters.firestore_repository import (
    FirestoreDocumentRepository,
    FirestoreUserConfigRepository,
)
from v2.domain.models import DocumentRecord
from v2.entrypoints.api.deps import (
    get_blob_storage,
    get_current_uid,
    get_document_repo,
    get_task_queue,
    get_user_config_repo,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

_FREE_PLAN_LIMIT = 5  # 無料プランの月間解析枚数上限


class UploadResponse(BaseModel):
    id: str
    status: str


class DocumentResponse(BaseModel):
    id: str
    status: str
    original_filename: str
    mime_type: str
    summary: str
    category: str
    error_message: str | None


def _to_response(record: DocumentRecord) -> DocumentResponse:
    return DocumentResponse(
        id=record.id,
        status=record.status,
        original_filename=record.original_filename,
        mime_type=record.mime_type,
        summary=record.summary,
        category=record.category,
        error_message=record.error_message,
    )


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED, response_model=UploadResponse)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    uid: str = Depends(get_current_uid),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
    storage: GCSBlobStorage = Depends(get_blob_storage),
    queue: CloudTasksQueue = Depends(get_task_queue),
) -> UploadResponse:
    """
    PDF / 画像ファイルをアップロードし、非同期解析をキューに追加する。

    - 無料プランは月 5 枚まで
    - コンテンツハッシュによる重複アップロードを検出（冪等性）
    - GCS にファイルを保存し、Firestore にステータスを記録
    - Cloud Tasks に解析ジョブをキューイング
    """
    # ── 無料プランのレート制限チェック ──────────────────────────────────────
    # DISABLE_RATE_LIMIT=true の場合はスキップ（開発環境用）
    user_settings = user_repo.get_user(uid)
    used = user_settings.get("documents_this_month", 0)
    if (
        not os.environ.get("DISABLE_RATE_LIMIT")
        and user_settings.get("plan", "free") == "free"
        and used >= _FREE_PLAN_LIMIT
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"無料プランの月間上限（{_FREE_PLAN_LIMIT}枚）に達しました。プレミアムプランへのアップグレードをご検討ください。",
        )

    content = await file.read()

    # ── 冪等性チェック（SHA-256 による重複排除） ────────────────────────────
    content_hash = hashlib.sha256(content).hexdigest()
    existing = doc_repo.find_by_content_hash(uid, content_hash)
    if existing:
        logger.info("Duplicate upload detected: uid=%s, hash=%s", uid, content_hash[:16])
        return UploadResponse(id=existing.id, status=existing.status)

    # ── GCS にファイルを保存 ─────────────────────────────────────────────────
    document_id = str(uuid.uuid4())
    mime_type = file.content_type or "application/octet-stream"
    ext = _ext_from_mime(mime_type)
    storage_path = f"uploads/{uid}/{document_id}{ext}"
    storage.upload(storage_path, content, mime_type)

    # ── Firestore にドキュメントレコードを作成（status=pending） ────────────
    record = DocumentRecord(
        id=document_id,
        uid=uid,
        status="pending",
        content_hash=content_hash,
        storage_path=storage_path,
        original_filename=file.filename or "unknown",
        mime_type=mime_type,
    )
    doc_repo.create(uid, record)

    # ── 解析ジョブをディスパッチ ──────────────────────────────────────────────
    payload = {
        "uid": uid,
        "document_id": document_id,
        "storage_path": storage_path,
        "mime_type": mime_type,
    }
    if os.environ.get("LOCAL_MODE"):
        # ローカル開発: Cloud Tasks を使わず同プロセスの BackgroundTasks で実行
        from v2.entrypoints.worker import run_analysis_sync
        background_tasks.add_task(run_analysis_sync, uid, document_id, storage_path, mime_type)
        logger.info("LOCAL_MODE: scheduled background analysis for doc_id=%s", document_id)
    else:
        queue.enqueue(payload)

    # ── 月間利用枚数をインクリメント ──────────────────────────────────────────
    user_repo.update_user(uid, {"documents_this_month": used + 1})

    logger.info("Document uploaded: uid=%s, doc_id=%s", uid, document_id)
    return UploadResponse(id=document_id, status="pending")


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    uid: str = Depends(get_current_uid),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
) -> list[DocumentResponse]:
    """ユーザーのドキュメント一覧を返す（新しい順）"""
    records = doc_repo.list(uid)
    return [_to_response(r) for r in records]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    uid: str = Depends(get_current_uid),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
) -> DocumentResponse:
    """指定ドキュメントの詳細を返す"""
    record = doc_repo.get(uid, document_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _to_response(record)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    uid: str = Depends(get_current_uid),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
    storage: GCSBlobStorage = Depends(get_blob_storage),
) -> None:
    """ドキュメントと GCS ファイルを削除する"""
    record = doc_repo.get(uid, document_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    storage.delete(record.storage_path)
    doc_repo.delete(uid, document_id)
    logger.info("Document deleted: uid=%s, doc_id=%s", uid, document_id)


def _ext_from_mime(mime_type: str) -> str:
    """MIME タイプからファイル拡張子を返す"""
    return {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/heic": ".heic",
    }.get(mime_type, "")
