"""プロファイル管理 API ルート

GET    /api/profiles         → 200 [UserProfile...]
POST   /api/profiles         → 201 { id, ... }
PUT    /api/profiles/{id}    → 200 { id, ... }
DELETE /api/profiles/{id}    → 204
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from v2.adapters.firestore_repository import FirestoreUserConfigRepository
from v2.domain.models import UserProfile
from v2.entrypoints.api.deps import get_current_uid, get_user_config_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileRequest(BaseModel):
    name: str
    grade: str
    keywords: str = ""


class ProfileResponse(BaseModel):
    id: str
    name: str
    grade: str
    keywords: str


@router.get("", response_model=list[ProfileResponse])
async def list_profiles(
    uid: str = Depends(get_current_uid),
    repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> list[ProfileResponse]:
    """プロファイル一覧を返す"""
    profiles = repo.list_profiles(uid)
    return [
        ProfileResponse(id=p.id, name=p.name, grade=p.grade, keywords=p.keywords)
        for p in profiles
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
async def create_profile(
    body: ProfileRequest,
    uid: str = Depends(get_current_uid),
    repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> ProfileResponse:
    """プロファイルを作成する"""
    profile = UserProfile(
        id="", name=body.name, grade=body.grade, keywords=body.keywords
    )
    profile_id = repo.create_profile(uid, profile)
    logger.info("Profile created: uid=%s, profile_id=%s", uid, profile_id)
    return ProfileResponse(
        id=profile_id, name=body.name, grade=body.grade, keywords=body.keywords
    )


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: str,
    body: ProfileRequest,
    uid: str = Depends(get_current_uid),
    repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> ProfileResponse:
    """プロファイルを更新する"""
    # 存在確認
    profiles = repo.list_profiles(uid)
    if not any(p.id == profile_id for p in profiles):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile = UserProfile(
        id=profile_id, name=body.name, grade=body.grade, keywords=body.keywords
    )
    repo.update_profile(uid, profile_id, profile)
    logger.info("Profile updated: uid=%s, profile_id=%s", uid, profile_id)
    return ProfileResponse(
        id=profile_id, name=body.name, grade=body.grade, keywords=body.keywords
    )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    uid: str = Depends(get_current_uid),
    repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> None:
    """プロファイルを削除する"""
    profiles = repo.list_profiles(uid)
    if not any(p.id == profile_id for p in profiles):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    repo.delete_profile(uid, profile_id)
    logger.info("Profile deleted: uid=%s, profile_id=%s", uid, profile_id)
