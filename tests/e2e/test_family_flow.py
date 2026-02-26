"""ファミリー作成 → 招待 → 参加フローの E2E テスト

Firestore Emulator を使って実際のリポジトリ層を経由したテストを行う。
"""

from __future__ import annotations

import pytest
from v2.entrypoints.api import deps
from v2.entrypoints.api.app import app

from tests.e2e.conftest import TEST_UID, TEST_UID_2

pytestmark = pytest.mark.e2e


class TestFamilyAutoCreate:
    """GET /api/families/me の初回アクセスで自動ファミリーが作成されることを確認"""

    def test_first_access_creates_family(self, e2e_client):
        """初回アクセスでファミリーが自動作成され 200 を返す"""
        r = e2e_client.get("/api/families/me")
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["name"] == "マイファミリー"
        assert data["plan"] == "free"
        assert data["role"] == "owner"
        assert data["documents_this_month"] == 0

    def test_repeated_access_returns_same_family(self, e2e_client):
        """同じユーザーが複数回アクセスしても同じ family_id を返す"""
        r1 = e2e_client.get("/api/families/me")
        r2 = e2e_client.get("/api/families/me")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]


class TestListMembers:
    """GET /api/families/members のテスト"""

    def test_initial_member_list_contains_owner(self, e2e_client):
        """初期状態でオーナー 1 人のみのメンバー一覧を返す"""
        # ファミリーを自動作成してから members を取得
        e2e_client.get("/api/families/me")

        r = e2e_client.get("/api/families/members")
        assert r.status_code == 200
        members = r.json()
        assert len(members) == 1
        assert members[0]["uid"] == TEST_UID
        assert members[0]["role"] == "owner"


class TestInvitationFlow:
    """招待フロー（invite → join → members 確認）の統合テスト"""

    def test_full_invitation_flow(self, e2e_client):
        """オーナーが招待 → 別ユーザーが参加 → メンバーが 2 人になる"""
        # User1: ファミリー自動作成
        r = e2e_client.get("/api/families/me")
        assert r.status_code == 200

        # User1: 招待 URL 生成
        r = e2e_client.post(
            "/api/families/invite",
            json={"email": "user2@example.com"},
        )
        assert r.status_code == 201
        invite_url = r.json()["invite_url"]
        token = invite_url.split("token=")[1]

        # User2 に切り替えて招待トークンで参加
        app.dependency_overrides[deps.get_current_uid] = lambda: TEST_UID_2
        r = e2e_client.post("/api/families/join", json={"token": token})
        assert r.status_code == 200
        join_data = r.json()
        assert join_data["role"] == "member"

        # User1 に戻してメンバー数を確認（2 人になっているはず）
        app.dependency_overrides[deps.get_current_uid] = lambda: TEST_UID
        r = e2e_client.get("/api/families/members")
        assert r.status_code == 200
        members = r.json()
        assert len(members) == 2
        roles = {m["uid"]: m["role"] for m in members}
        assert roles[TEST_UID] == "owner"
        assert roles[TEST_UID_2] == "member"

    def test_used_token_is_rejected(self, e2e_client):
        """使用済み招待トークンは 400 を返す"""
        # User1: 招待作成
        e2e_client.get("/api/families/me")
        r = e2e_client.post(
            "/api/families/invite",
            json={"email": "user2@example.com"},
        )
        token = r.json()["invite_url"].split("token=")[1]

        # User2: 初回参加（成功）
        app.dependency_overrides[deps.get_current_uid] = lambda: TEST_UID_2
        r = e2e_client.post("/api/families/join", json={"token": token})
        assert r.status_code == 200

        # User2: 同じトークンで再度参加しようとする → 400
        r = e2e_client.post("/api/families/join", json={"token": token})
        assert r.status_code == 400

    def test_member_cannot_invite(self, e2e_client):
        """メンバーは招待できない（403）"""
        # User1: ファミリー作成 + User2 を招待
        e2e_client.get("/api/families/me")
        r = e2e_client.post(
            "/api/families/invite",
            json={"email": "user2@example.com"},
        )
        token = r.json()["invite_url"].split("token=")[1]

        # User2: 参加
        app.dependency_overrides[deps.get_current_uid] = lambda: TEST_UID_2
        e2e_client.post("/api/families/join", json={"token": token})

        # User2 がメンバーとして招待しようとする → 403
        r = e2e_client.post(
            "/api/families/invite",
            json={"email": "user3@example.com"},
        )
        assert r.status_code == 403

    def test_invalid_token_returns_404(self, e2e_client):
        """存在しないトークンは 404 を返す"""
        e2e_client.get("/api/families/me")
        r = e2e_client.post(
            "/api/families/join",
            json={"token": "00000000-0000-0000-0000-000000000000"},
        )
        assert r.status_code == 404
