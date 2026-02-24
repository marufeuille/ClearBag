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
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from v2.entrypoints.api.routes import (
    documents,
    events,
    ical,
    profiles,
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://clearbag.app",
        "https://clearbag-dev.web.app",
        "http://localhost:3000",  # ローカル開発用
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ルーター登録 ─────────────────────────────────────────────────────────────
_PREFIX = "/api"

app.include_router(documents.router, prefix=_PREFIX)
app.include_router(events.router, prefix=_PREFIX)
app.include_router(tasks.router, prefix=_PREFIX)
app.include_router(profiles.router, prefix=_PREFIX)
app.include_router(ical.router, prefix=_PREFIX)
app.include_router(settings.router, prefix=_PREFIX)


@app.get("/health")
async def health() -> dict:
    """ヘルスチェックエンドポイント（Cloud Run の起動確認用）"""
    return {"status": "ok"}


logger.info("ClearBag API started")
