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

import base64
import json
import logging
import os
import time
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from v2.analytics import log_event
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

# ── ミドルウェア登録順の注意 ────────────────────────────────────────────────────
# add_middleware は後から登録したものが外側になる（insert(0, ...) のため）。
# @app.middleware デコレータは定義順に登録されるため、後に定義されたものが外側になる。
#
# スタック:
#   ServerErrorMiddleware
#     → CORSMiddleware          (後から add_middleware で最外側に配置)
#       → _catch_unhandled_exceptions  (後定義 = 外側)
#         → _log_access               (先定義 = 内側: HTTPException は正常レスポンスとして記録)
#           → ExceptionMiddleware → Routes


def _extract_uid_from_bearer(request: Request) -> str | None:
    """Authorization: Bearer <JWT> から UID を取得する（署名検証なし・ログ用途のみ）。

    JWT payload を Base64url デコードするだけで、署名検証は行わない。
    ルートの get_auth_info による full verify とは独立している。
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    parts = auth_header[7:].split(".")
    if len(parts) != 3:
        return None
    try:
        payload_b64 = parts[1]
        # Base64url のパディング補完
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        # Firebase JWT は "user_id" (Firebase) または "sub" (標準) に UID を格納する
        return payload.get("user_id") or payload.get("sub")
    except Exception:
        return None


@app.middleware("http")
async def _log_access(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    """アクセスログミドルウェア（内側配置: ExceptionMiddleware より外、例外キャッチMWより内）。

    /health と /worker/* は除外する。
    """
    start = time.monotonic()
    response = await call_next(request)
    path = request.url.path
    if path == "/health" or path.startswith("/worker/"):
        return response
    uid = _extract_uid_from_bearer(request)
    log_event(
        "access_log",
        uid=uid,
        method=request.method,
        path=path,
        status_code=response.status_code,
        response_time_ms=round((time.monotonic() - start) * 1000),
    )
    return response


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
