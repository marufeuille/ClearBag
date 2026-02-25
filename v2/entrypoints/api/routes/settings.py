"""ユーザー設定 API ルート

GET   /api/settings  → ユーザー設定（plan, documentsThisMonth, icalUrl 等）
PATCH /api/settings  → 設定を部分更新（notification preferences 等）
"""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from v2.adapters.firestore_repository import FirestoreUserConfigRepository
from v2.entrypoints.api.deps import get_current_uid, get_user_config_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

_API_BASE_URL = os.environ.get("API_BASE_URL", "")


class SettingsResponse(BaseModel):
    plan: str
    documents_this_month: int
    ical_url: str
    notification_email: bool
    notification_web_push: bool


class SettingsUpdateRequest(BaseModel):
    notification_email: bool | None = None
    notification_web_push: bool | None = None


@router.get("", response_model=SettingsResponse)
async def get_settings(
    uid: str = Depends(get_current_uid),
    repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> SettingsResponse:
    """ユーザー設定を返す"""
    user = repo.get_user(uid)

    # icalToken が未設定の場合は初期化
    ical_token = user.get("ical_token")
    if not ical_token:
        ical_token = str(uuid.uuid4())
        repo.update_user(uid, {"ical_token": ical_token})

    ical_url = f"{_API_BASE_URL}/api/ical/{ical_token}"

    prefs = user.get("notification_preferences", {})
    return SettingsResponse(
        plan=user.get("plan", "free"),
        documents_this_month=user.get("documents_this_month", 0),
        ical_url=ical_url,
        notification_email=prefs.get("email", True),
        notification_web_push=prefs.get("web_push", False),
    )


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    uid: str = Depends(get_current_uid),
    repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> SettingsResponse:
    """設定を部分更新する"""
    update: dict = {}
    if body.notification_email is not None:
        update["notification_preferences.email"] = body.notification_email
    if body.notification_web_push is not None:
        update["notification_preferences.web_push"] = body.notification_web_push

    if update:
        repo.update_user(uid, update)
        logger.info("Settings updated: uid=%s, fields=%s", uid, list(update.keys()))

    return await get_settings(uid=uid, repo=repo)
