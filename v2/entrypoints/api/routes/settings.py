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

from v2.adapters.firestore_repository import (
    FirestoreFamilyRepository,
    FirestoreUserConfigRepository,
)
from v2.entrypoints.api.deps import (
    FamilyContext,
    get_family_context,
    get_family_repo,
    get_user_config_repo,
)
from v2.entrypoints.api.usage import ensure_monthly_reset

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
    ctx: FamilyContext = Depends(get_family_context),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
    family_repo: FirestoreFamilyRepository = Depends(get_family_repo),
) -> SettingsResponse:
    """ユーザー設定を返す"""
    user = user_repo.get_user(ctx.uid)
    family = family_repo.get_family(ctx.family_id) or {}
    family = ensure_monthly_reset(family_repo, ctx.family_id, family)

    # icalToken が未設定の場合は初期化（個人単位）
    ical_token = user.get("ical_token")
    if not ical_token:
        ical_token = str(uuid.uuid4())
        user_repo.update_user(ctx.uid, {"ical_token": ical_token})

    ical_url = f"{_API_BASE_URL}/api/ical/{ical_token}"

    # 通知設定は個人単位、課金情報はファミリー単位
    prefs = user.get("notification_preferences", {})
    return SettingsResponse(
        plan=family.get("plan", "free"),
        documents_this_month=family.get("documents_this_month", 0),
        ical_url=ical_url,
        notification_email=prefs.get("email", True),
        notification_web_push=prefs.get("web_push", False),
    )


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    ctx: FamilyContext = Depends(get_family_context),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
    family_repo: FirestoreFamilyRepository = Depends(get_family_repo),
) -> SettingsResponse:
    """設定を部分更新する"""
    update: dict = {}
    if body.notification_email is not None:
        update["notification_preferences.email"] = body.notification_email
    if body.notification_web_push is not None:
        update["notification_preferences.web_push"] = body.notification_web_push

    if update:
        user_repo.update_user(ctx.uid, update)
        logger.info("Settings updated: uid=%s, fields=%s", ctx.uid, list(update.keys()))

    return await get_settings(ctx=ctx, user_repo=user_repo, family_repo=family_repo)
