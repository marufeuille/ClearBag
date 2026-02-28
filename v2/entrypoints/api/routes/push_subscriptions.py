"""Push サブスクリプション管理 API ルート

POST   /api/push-subscriptions             → Web Push サブスクリプションを登録
POST   /api/push-subscriptions/unsubscribe → Web Push サブスクリプションを削除
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from google.cloud.firestore import DELETE_FIELD
from pydantic import BaseModel

from v2.adapters.firestore_repository import FirestoreUserConfigRepository
from v2.entrypoints.api.deps import (
    FamilyContext,
    get_family_context,
    get_user_config_repo,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/push-subscriptions", tags=["push-subscriptions"])


class PushSubscriptionKeys(BaseModel):
    auth: str
    p256dh: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


@router.post("", status_code=204)
async def register_push_subscription(
    body: PushSubscriptionRequest,
    ctx: FamilyContext = Depends(get_family_context),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> None:
    """ブラウザの Push サブスクリプションを Firestore に保存する"""
    user_repo.update_user(
        ctx.uid,
        {
            "web_push_subscription": {
                "endpoint": body.endpoint,
                "keys": body.keys.model_dump(),
            }
        },
    )
    logger.info("Push subscription registered: uid=%s", ctx.uid)


@router.post("/unsubscribe", status_code=204)
async def unregister_push_subscription(
    ctx: FamilyContext = Depends(get_family_context),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> None:
    """Firestore から Push サブスクリプションを削除する"""
    user_repo.update_user(ctx.uid, {"web_push_subscription": DELETE_FIELD})
    logger.info("Push subscription removed: uid=%s", ctx.uid)
