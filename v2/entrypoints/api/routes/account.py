"""アカウント削除 API ルート

DELETE /api/account → 204 No Content
"""

from __future__ import annotations

import logging

import firebase_admin.auth as fb_auth
from fastapi import APIRouter, Depends, HTTPException, status

from v2.adapters.cloud_storage import GCSBlobStorage
from v2.adapters.firestore_repository import (
    FirestoreFamilyRepository,
    FirestoreUserConfigRepository,
)
from v2.entrypoints.api.deps import (
    FamilyContext,
    get_blob_storage,
    get_family_context,
    get_family_repo,
    get_user_config_repo,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["account"])


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    ctx: FamilyContext = Depends(get_family_context),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
    family_repo: FirestoreFamilyRepository = Depends(get_family_repo),
    blob_storage: GCSBlobStorage = Depends(get_blob_storage),
) -> None:
    """
    アカウントを完全削除する。

    - オーナーかつ1人のみ: ファミリーごと全削除
    - オーナーかつ他メンバーがいる場合: 400エラー（先にメンバーを削除してください）
    - メンバー（非オーナー）: 自分のデータのみ削除
    """
    uid = ctx.uid
    family_id = ctx.family_id

    if ctx.role == "owner":
        members = family_repo.list_members(family_id)
        other_members = [m for m in members if m["uid"] != uid]
        if other_members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="他のメンバーがいるため削除できません。先にメンバーを削除するか、オーナー権限を移譲してください。",
            )
        # GCS 一括削除
        blob_storage.delete_by_prefix(f"uploads/{family_id}/")
        # Firestore ファミリー全削除
        family_repo.delete_family_cascade(family_id)
    else:
        # メンバー自身のレコードのみ削除
        family_repo.remove_member(family_id, uid)

    # users/{uid} 削除
    user_repo.delete_user(uid)
    # Firebase Auth アカウント削除
    try:
        fb_auth.delete_user(uid)
    except Exception:
        logger.warning("Failed to delete Firebase Auth user: uid=%s", uid)

    logger.info(
        "Account deleted: uid=%s, family_id=%s, role=%s", uid, family_id, ctx.role
    )
