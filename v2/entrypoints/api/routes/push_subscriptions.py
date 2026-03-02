"""Push サブスクリプション管理 API ルート

POST   /api/push-subscriptions             → Web Push サブスクリプションを登録
POST   /api/push-subscriptions/unsubscribe → Web Push サブスクリプションを削除

Firestore スキーマ（端末 Map 方式）:
  users/{uid}/web_push_subscriptions: {
    "<sha256_hex[:16]>": { endpoint, keys },
    ...
  }
"""

from __future__ import annotations

import hashlib
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


def _endpoint_key(endpoint: str) -> str:
    """endpoint の SHA256 ハッシュ先頭 16 文字を返す（Firestore Map のキーとして使用）"""
    return hashlib.sha256(endpoint.encode()).hexdigest()[:16]


class PushSubscriptionKeys(BaseModel):
    auth: str
    p256dh: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class UnsubscribeRequest(BaseModel):
    endpoint: str | None = None


@router.post("", status_code=204)
def register_push_subscription(
    body: PushSubscriptionRequest,
    ctx: FamilyContext = Depends(get_family_context),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> None:
    """ブラウザの Push サブスクリプションを Firestore に保存する（端末単位 Map）"""
    key = _endpoint_key(body.endpoint)
    user_repo.update_user(
        ctx.uid,
        {
            f"web_push_subscriptions.{key}": {
                "endpoint": body.endpoint,
                "keys": body.keys.model_dump(),
            }
        },
    )
    logger.info("Push subscription registered: uid=%s, key=%s", ctx.uid, key)


@router.post("/unsubscribe", status_code=204)
def unregister_push_subscription(
    body: UnsubscribeRequest | None = None,
    ctx: FamilyContext = Depends(get_family_context),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> None:
    """Firestore から Push サブスクリプションを削除する。

    endpoint が指定された場合は該当端末のみ削除する。
    指定なし（旧クライアントや SW キャッシュ由来のリクエスト）の場合は
    全サブスクリプションを削除する（後方互換）。
    """
    if body and body.endpoint:
        key = _endpoint_key(body.endpoint)
        user_repo.update_user(ctx.uid, {f"web_push_subscriptions.{key}": DELETE_FIELD})
        logger.info("Push subscription removed: uid=%s, key=%s", ctx.uid, key)
    else:
        # endpoint なし: 全サブスクリプション削除（旧 SW キャッシュからのリクエスト等）
        user_repo.update_user(
            ctx.uid,
            {
                "web_push_subscriptions": DELETE_FIELD,
                "web_push_subscription": DELETE_FIELD,
            },
        )
        logger.info("All push subscriptions removed (no endpoint): uid=%s", ctx.uid)
