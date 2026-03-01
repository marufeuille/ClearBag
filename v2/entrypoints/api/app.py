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
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

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

# ── グローバル例外ミドルウェア ──────────────────────────────────────────────────
# 【登録順の注意】
#   add_middleware は後から登録したものが外側になる（insert(0, ...) のため）。
#   このミドルウェアを CORSMiddleware より先に登録することで内側に配置し、
#   500 レスポンスが CORSMiddleware を通過して CORS ヘッダーが付与される。
#
# スタック: ServerErrorMiddleware → CORSMiddleware → このMW → ExceptionMiddleware → Routes


@app.middleware("http")
async def _catch_unhandled_exceptions(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error(
            "Unhandled exception: %s %s - %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


# ── CORS（PWA フロントエンドからのリクエストを許可） ─────────────────────────
# CORS_ORIGINS 環境変数でカンマ区切りの追加オリジンを指定可能
# 【後から登録 = 外側】例外ミドルウェアを内包し、全レスポンスに CORS ヘッダーを付与する
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
