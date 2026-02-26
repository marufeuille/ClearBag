"""ファミリー管理 API ルート

POST   /api/families           → 201 { id, name, role }
GET    /api/families/me        → 200 { id, name, plan, ... }
GET    /api/families/members   → 200 [{ uid, role, display_name, email }...]
POST   /api/families/invite    → 201 { invitation_id, invite_url } （Phase 2）
POST   /api/families/join      → 200 { family_id, name, role }   （Phase 2）
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
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
    require_owner,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/families", tags=["families"])


# ── レスポンスモデル ─────────────────────────────────────────────────────────────


class FamilyCreateRequest(BaseModel):
    name: str = "マイファミリー"


class FamilyResponse(BaseModel):
    id: str
    name: str
    plan: str
    documents_this_month: int
    role: str


class MemberResponse(BaseModel):
    uid: str
    role: str
    display_name: str
    email: str


class InviteRequest(BaseModel):
    email: str


class InviteResponse(BaseModel):
    invitation_id: str
    invite_url: str


class JoinRequest(BaseModel):
    token: str


class JoinResponse(BaseModel):
    family_id: str
    name: str
    role: str


# ── エンドポイント ────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FamilyResponse)
async def create_family(
    body: FamilyCreateRequest,
    ctx: FamilyContext = Depends(get_family_context),
    family_repo: FirestoreFamilyRepository = Depends(get_family_repo),
) -> FamilyResponse:
    """
    ファミリーを作成する。

    注意: get_family_context() が初回アクセス時に自動でファミリーを作成するため、
    このエンドポイントはファミリー名を変更する目的で使用する。
    """
    family_repo.update_family(ctx.family_id, {"name": body.name})
    logger.info("Family name updated: family_id=%s, name=%s", ctx.family_id, body.name)

    family = family_repo.get_family(ctx.family_id) or {}
    return FamilyResponse(
        id=ctx.family_id,
        name=family.get("name", body.name),
        plan=family.get("plan", "free"),
        documents_this_month=family.get("documents_this_month", 0),
        role=ctx.role,
    )


@router.get("/me", response_model=FamilyResponse)
async def get_my_family(
    ctx: FamilyContext = Depends(get_family_context),
    family_repo: FirestoreFamilyRepository = Depends(get_family_repo),
) -> FamilyResponse:
    """自分のファミリー情報を返す"""
    family = family_repo.get_family(ctx.family_id)
    if family is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Family not found"
        )
    return FamilyResponse(
        id=ctx.family_id,
        name=family.get("name", "マイファミリー"),
        plan=family.get("plan", "free"),
        documents_this_month=family.get("documents_this_month", 0),
        role=ctx.role,
    )


@router.get("/members", response_model=list[MemberResponse])
async def list_members(
    ctx: FamilyContext = Depends(get_family_context),
    family_repo: FirestoreFamilyRepository = Depends(get_family_repo),
) -> list[MemberResponse]:
    """ファミリーメンバー一覧を返す"""
    members = family_repo.list_members(ctx.family_id)
    return [
        MemberResponse(
            uid=m.get("uid", ""),
            role=m.get("role", "member"),
            display_name=m.get("display_name", ""),
            email=m.get("email", ""),
        )
        for m in members
    ]


@router.post(
    "/invite", status_code=status.HTTP_201_CREATED, response_model=InviteResponse
)
async def invite_member(
    body: InviteRequest,
    ctx: FamilyContext = Depends(require_owner),
    family_repo: FirestoreFamilyRepository = Depends(get_family_repo),
) -> InviteResponse:
    """
    メンバーを招待する（オーナーのみ）。

    招待トークンを含む URL を生成する。
    招待先はこの URL にアクセスして POST /api/families/join を呼び出す。
    """
    import os

    token = str(uuid.uuid4())
    invitation_id = family_repo.create_invitation(
        family_id=ctx.family_id,
        email=body.email,
        invited_by_uid=ctx.uid,
        token=token,
    )

    api_base_url = os.environ.get("API_BASE_URL", "")
    invite_url = f"{api_base_url}/invite?token={token}"

    logger.info(
        "Invitation created: family_id=%s, email=%s, invitation_id=%s",
        ctx.family_id,
        body.email,
        invitation_id,
    )
    return InviteResponse(invitation_id=invitation_id, invite_url=invite_url)


@router.post("/join", response_model=JoinResponse)
async def join_family(
    body: JoinRequest,
    ctx: FamilyContext = Depends(get_family_context),
    family_repo: FirestoreFamilyRepository = Depends(get_family_repo),
    user_repo: FirestoreUserConfigRepository = Depends(get_user_config_repo),
) -> JoinResponse:
    """
    招待トークンを使ってファミリーに参加する。

    1. トークンで招待情報を取得
    2. 有効な招待（pending かつ期限内）であることを確認
    3. 現在のファミリーを離れて新しいファミリーに参加
    4. users/{uid} の family_id を更新
    """
    import datetime

    invitation = family_repo.get_invitation_by_token(body.token)
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token"
        )

    if invitation.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この招待はすでに使用済みまたは期限切れです。",
        )

    expires_at = invitation.get("expires_at")
    if expires_at and expires_at < datetime.datetime.now(datetime.UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="招待の有効期限が切れています。",
        )

    new_family_id = invitation["family_id"]
    new_family = family_repo.get_family(new_family_id)
    if new_family is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Family not found"
        )

    # メンバーとして追加
    user = user_repo.get_user(ctx.uid)
    family_repo.add_member(
        family_id=new_family_id,
        uid=ctx.uid,
        role="member",
        display_name=user.get("display_name", user.get("email", ctx.uid)),
        email=user.get("email", ""),
    )

    # users/{uid} の family_id を更新
    user_repo.update_user(ctx.uid, {"family_id": new_family_id})

    # 招待を accepted に更新
    family_repo.accept_invitation(invitation["id"], new_family_id)

    logger.info("User joined family: uid=%s, family_id=%s", ctx.uid, new_family_id)
    return JoinResponse(
        family_id=new_family_id,
        name=new_family.get("name", "マイファミリー"),
        role="member",
    )
