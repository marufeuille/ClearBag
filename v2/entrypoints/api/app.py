"""FastAPI アプリケーション

ClearBag B2C バックエンド API。
Cloud Run Service として動作し、Firebase Auth で認証する。

エンドポイント一覧:
  POST   /api/documents/upload
  GET    /api/documents
  GET    /api/documents/{id}
  DELETE /api/documents/{id}
  GET    /api/events
  GET    /api/tasks
  PATCH  /api/tasks/{id}
  GET    /api/profiles
  POST   /api/profiles
  PUT    /api/profiles/{id}
  DELETE /api/profiles/{id}
  GET    /api/ical/{token}     ← 認証不要
  GET    /api/settings
  PATCH  /api/settings
  POST   /api/push-subscriptions
  POST   /api/push-subscriptions/unsubscribe
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from v2.entrypoints import worker
from v2.entrypoints.api.routes import (
    documents,
    events,
    families,
    ical,
    profiles,
    push_subscriptions,
    settings,
    tasks,
)
from v2.logging_config import setup_logging

# ── ロギング初期化 ───────────────────────────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)

# ── FastAPI アプリ ───────────────────────────────────────────────────────────
app = FastAPI(
    title="ClearBag API",
    description="学校配布物AIアシスタント ClearBag のバックエンド API",
    version="1.0.0",
)

# ── CORS（PWA フロントエンドからのリクエストを許可） ─────────────────────────
# CORS_ORIGINS 環境変数でカンマ区切りの追加オリジンを指定可能
_extra_origins = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_extra_origins if _extra_origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── ルーター登録 ─────────────────────────────────────────────────────────────
_PREFIX = "/api"

app.include_router(documents.router, prefix=_PREFIX)
app.include_router(events.router, prefix=_PREFIX)
app.include_router(tasks.router, prefix=_PREFIX)
app.include_router(profiles.router, prefix=_PREFIX)
app.include_router(families.router, prefix=_PREFIX)
app.include_router(ical.router, prefix=_PREFIX)
app.include_router(settings.router, prefix=_PREFIX)
app.include_router(push_subscriptions.router, prefix=_PREFIX)

# ── Cloud Tasks ワーカールート（/worker/*）────────────────────────────────────
# Firebase Auth なし。アプリレベルの OIDC トークン検証（verify_worker_token）で保護される。
app.include_router(worker.router, prefix="/worker")


@app.on_event("startup")
async def _on_startup() -> None:
    """LOCAL_MODE 時にエミュレーター上の GCS バケットを自動作成する"""
    if os.environ.get("LOCAL_MODE"):
        bucket_name = os.environ.get("GCS_BUCKET_NAME", "clearbag-local")
        try:
            from google.cloud import storage as gcs

            client = gcs.Client()
            if not client.bucket(bucket_name).exists():
                client.create_bucket(bucket_name)
                logger.info("LOCAL_MODE: created GCS bucket '%s'", bucket_name)
        except Exception:
            logger.warning(
                "LOCAL_MODE: could not auto-create GCS bucket (may already exist)"
            )


@app.get("/health")
async def health() -> dict:
    """ヘルスチェックエンドポイント（Cloud Run の起動確認用）"""
    return {"status": "ok"}


logger.info("ClearBag API started")
