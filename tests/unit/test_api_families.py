"""FastAPI ファミリー API のユニットテスト

dependency_overrides を使ってリポジトリをモックに差し替える。
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import (
    AuthInfo,
    FamilyContext,
    get_auth_info,
    get_family_context,
    get_family_repo,
    get_user_config_repo,
    require_owner,
)

_UID = "test-owner-uid"
_FAMILY_ID = "test-family-id"
_OWNER_CONTEXT = FamilyContext(uid=_UID, family_id=_FAMILY_ID, role="owner")
_MEMBER_CONTEXT = FamilyContext(uid="member-uid", family_id=_FAMILY_ID, role="member")
_JOIN_AUTH_INFO = AuthInfo(
    uid="join-uid", email="joiner@example.com", display_name="Joiner"
)


@pytest.fixture
def mock_family_repo():
    repo = MagicMock()
    repo.get_family.return_value = {
        "name": "田中家",
        "plan": "free",
        "documents_this_month": 3,
        "owner_uid": _UID,
    }
    repo.list_members.return_value = [
        {
            "uid": _UID,
            "role": "owner",
            "display_name": "パパ",
            "email": "papa@example.com",
        }
    ]
    repo.create_invitation.return_value = "inv-test-id"
    repo.get_invitation_by_token.return_value = None
    return repo


@pytest.fixture
def mock_user_repo():
    repo = MagicMock()
    repo.get_user.return_value = {"email": "papa@example.com", "display_name": "パパ"}
    return repo


@pytest.fixture
def owner_client(mock_family_repo, mock_user_repo):
    """オーナー権限のテストクライアント"""
    app.dependency_overrides[get_family_context] = lambda: _OWNER_CONTEXT
    app.dependency_overrides[require_owner] = lambda: _OWNER_CONTEXT
    app.dependency_overrides[get_family_repo] = lambda: mock_family_repo
    app.dependency_overrides[get_user_config_repo] = lambda: mock_user_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def member_client(mock_family_repo, mock_user_repo):
    """メンバー権限のテストクライアント（招待ができないケース用）"""
    app.dependency_overrides[get_family_context] = lambda: _MEMBER_CONTEXT
    app.dependency_overrides[require_owner] = _raise_forbidden
    app.dependency_overrides[get_family_repo] = lambda: mock_family_repo
    app.dependency_overrides[get_user_config_repo] = lambda: mock_user_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def join_client(mock_family_repo, mock_user_repo):
    """join_family() 用テストクライアント（get_auth_info を override）"""
    app.dependency_overrides[get_auth_info] = lambda: _JOIN_AUTH_INFO
    app.dependency_overrides[get_family_repo] = lambda: mock_family_repo
    app.dependency_overrides[get_user_config_repo] = lambda: mock_user_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _raise_forbidden():
    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="この操作にはオーナー権限が必要です。",
    )


class TestGetMyFamily:
    """GET /api/families/me のテスト"""

    def test_returns_family_info(self, owner_client):
        """ファミリー情報を返す"""
        response = owner_client.get("/api/families/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == _FAMILY_ID
        assert data["name"] == "田中家"
        assert data["plan"] == "free"
        assert data["role"] == "owner"

    def test_returns_404_if_family_not_found(self, owner_client, mock_family_repo):
        """ファミリーが存在しない場合は 404 を返す"""
        mock_family_repo.get_family.return_value = None
        response = owner_client.get("/api/families/me")
        assert response.status_code == 404


class TestListMembers:
    """GET /api/families/members のテスト"""

    def test_returns_member_list(self, owner_client):
        """メンバー一覧を返す"""
        response = owner_client.get("/api/families/members")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["uid"] == _UID
        assert data[0]["role"] == "owner"

    def test_member_can_list_members(self, member_client):
        """メンバーもメンバー一覧を参照できる"""
        response = member_client.get("/api/families/members")
        assert response.status_code == 200


class TestInviteMember:
    """POST /api/families/invite のテスト"""

    def test_owner_can_invite(self, owner_client, mock_family_repo):
        """オーナーは招待できる"""
        response = owner_client.post(
            "/api/families/invite",
            json={"email": "mama@example.com"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "invitation_id" in data
        assert "invite_url" in data

    def test_member_cannot_invite(self, member_client):
        """メンバーは招待できない（403 を返す）"""
        response = member_client.post(
            "/api/families/invite",
            json={"email": "someone@example.com"},
        )
        assert response.status_code == 403


class TestJoinFamily:
    """POST /api/families/join のテスト"""

    def test_invalid_token_returns_404(self, join_client, mock_family_repo):
        """無効なトークンは 404 を返す"""
        mock_family_repo.get_invitation_by_token.return_value = None
        response = join_client.post(
            "/api/families/join",
            json={"token": "invalid-token"},
        )
        assert response.status_code == 404

    def test_already_accepted_invitation_returns_400(
        self, join_client, mock_family_repo
    ):
        """使用済み招待は 400 を返す"""
        mock_family_repo.get_invitation_by_token.return_value = {
            "id": "inv-id",
            "family_id": "other-family-id",
            "status": "accepted",
            "token": "some-token",
        }
        response = join_client.post(
            "/api/families/join",
            json={"token": "some-token"},
        )
        assert response.status_code == 400

    def test_email_mismatch_returns_403(self, join_client, mock_family_repo):
        """招待 email とログイン email が不一致の場合 403 EMAIL_MISMATCH を返す"""
        # _JOIN_AUTH_INFO.email = "joiner@example.com" だが招待は別の email 宛て
        mock_family_repo.get_invitation_by_token.return_value = {
            "id": "inv-id",
            "family_id": _FAMILY_ID,
            "status": "pending",
            "email": "other@example.com",
            "token": "some-token",
        }
        response = join_client.post(
            "/api/families/join",
            json={"token": "some-token"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "EMAIL_MISMATCH"

    def test_successful_join_activates_user(
        self, join_client, mock_family_repo, mock_user_repo
    ):
        """正常な join で is_activated: True がセットされる"""
        mock_family_repo.get_invitation_by_token.return_value = {
            "id": "inv-id",
            "family_id": _FAMILY_ID,
            "status": "pending",
            "email": "joiner@example.com",  # _JOIN_AUTH_INFO.email と一致
            "token": "valid-token",
        }
        mock_family_repo.get_family.return_value = {
            "name": "田中家",
            "plan": "free",
            "documents_this_month": 0,
        }
        response = join_client.post(
            "/api/families/join",
            json={"token": "valid-token"},
        )
        assert response.status_code == 200
        # is_activated: True が update_user に渡されていることを確認
        mock_user_repo.update_user.assert_called_once_with(
            _JOIN_AUTH_INFO.uid,
            {"family_id": _FAMILY_ID, "is_activated": True},
        )
