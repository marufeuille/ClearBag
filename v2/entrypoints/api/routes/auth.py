"""認証関連 API ルート

POST /api/auth/register — サービス招待コードでユーザーをアクティベート
"""

from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from pydantic import BaseModel

from v2.entrypoints.api.deps import AuthInfo, _get_firestore_client, get_auth_info

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_SERVICE_CODES = "service_codes"
_USERS = "users"


class RegisterRequest(BaseModel):
    code: str


class RegisterResponse(BaseModel):
    activated: bool
    message: str


@router.post("/register", response_model=RegisterResponse)
def register_with_code(
    body: RegisterRequest,
    auth_info: AuthInfo = Depends(get_auth_info),
) -> RegisterResponse:
    """
    サービス招待コードを使ってユーザーをアクティベートする。

    依存: get_auth_info（未アクティベートユーザーが呼ぶため get_family_context は不使用）

    処理フロー:
    1. service_codes/{code} を取得 → 存在しなければ 404 INVALID_CODE
    2. expires_at チェック → 期限切れなら 400 CODE_EXPIRED
    3. max_uses チェック → 上限超過なら 400 CODE_EXHAUSTED
    4. 既に is_activated: True なら 200 返却（冪等）
    5. Firestore トランザクションで used_count インクリメント + is_activated: True セット
    6. 200 返却
    """
    db = _get_firestore_client()
    code_ref = db.collection(_SERVICE_CODES).document(body.code)
    code_doc = code_ref.get()

    if not code_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="INVALID_CODE",
        )

    code_data = code_doc.to_dict() or {}

    expires_at = code_data.get("expires_at")
    if expires_at and expires_at < datetime.datetime.now(datetime.UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CODE_EXPIRED",
        )

    max_uses = code_data.get("max_uses")
    used_count = code_data.get("used_count", 0)
    if max_uses is not None and used_count >= max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CODE_EXHAUSTED",
        )

    # 既にアクティベート済みなら冪等に 200 返却
    user_ref = db.collection(_USERS).document(auth_info.uid)
    user_doc = user_ref.get()
    if (user_doc.to_dict() or {}).get("is_activated", False):
        logger.info(
            "register_with_code: already activated uid=%s code=%s",
            auth_info.uid,
            body.code,
        )
        return RegisterResponse(activated=True, message="登録済みです")

    # Firestore トランザクションで used_count インクリメント + is_activated セット
    @firestore.transactional
    def _activate(transaction: firestore.Transaction) -> None:
        snap = code_ref.get(transaction=transaction)
        data = snap.to_dict() or {}
        current_used = data.get("used_count", 0)
        current_max = data.get("max_uses")
        if current_max is not None and current_used >= current_max:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CODE_EXHAUSTED",
            )
        transaction.update(code_ref, {"used_count": current_used + 1})
        transaction.set(user_ref, {"is_activated": True}, merge=True)

    transaction = db.transaction()
    _activate(transaction)

    logger.info(
        "register_with_code: activated uid=%s code=%s",
        auth_info.uid,
        body.code,
    )
    return RegisterResponse(activated=True, message="登録が完了しました。ダッシュボードへ移動します。")
