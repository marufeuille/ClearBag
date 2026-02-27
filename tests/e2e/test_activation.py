"""アクティベーションフローの E2E テスト

- 未アクティベートユーザーは get_family_context を通じて 403 ACTIVATION_REQUIRED を受け取る
- join フローでアクティベートされる
- 招待 email 不一致は 403 EMAIL_MISMATCH を返す
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from v2.entrypoints.api import deps
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import AuthInfo

from tests.e2e.conftest import TEST_UID, TEST_UID_2

pytestmark = pytest.mark.e2e

_UNACTIVATED_UID = "unactivated-user"
_UNACTIVATED_EMAIL = "unactivated@example.com"


@pytest.fixture
def unactivated_client(firestore_client):
    """未アクティベートユーザーの TestClient。

    Firestore に is_activated を設定しないため、get_family_context で 403 になる。
    """
    deps._firestore_client = firestore_client

    mock_blob = MagicMock()
    mock_blob.upload.return_value = "uploads/test.pdf"

    app.dependency_overrides[deps.get_auth_info] = lambda: AuthInfo(
        uid=_UNACTIVATED_UID,
        email=_UNACTIVATED_EMAIL,
        display_name="Unactivated User",
    )
    app.dependency_overrides[deps.get_blob_storage] = lambda: mock_blob
    app.dependency_overrides[deps.get_task_queue] = lambda: None

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    deps._firestore_client = None


class TestActivationRequired:
    """未アクティベートユーザーのアクセス制御テスト"""

    def test_unactivated_user_gets_403(self, unactivated_client):
        """未アクティベートユーザーが /api/families/me にアクセスすると 403 ACTIVATION_REQUIRED"""
        r = unactivated_client.get("/api/families/me")
        assert r.status_code == 403
        assert r.json()["detail"] == "ACTIVATION_REQUIRED"

    def test_unactivated_user_cannot_access_documents(self, unactivated_client):
        """未アクティベートユーザーが /api/documents にアクセスすると 403"""
        r = unactivated_client.get("/api/documents")
        assert r.status_code == 403
        assert r.json()["detail"] == "ACTIVATION_REQUIRED"


class TestJoinActivation:
    """join フローによるアクティベーションテスト"""

    def test_join_activates_user(self, e2e_client, firestore_client):
        """招待 join でユーザーが is_activated: True になる"""
        # User1（e2e_client / TEST_UID）がファミリーを作成して招待を発行
        r = e2e_client.get("/api/families/me")
        assert r.status_code == 200

        r = e2e_client.post(
            "/api/families/invite",
            json={"email": _UNACTIVATED_EMAIL},
        )
        assert r.status_code == 201
        token = r.json()["invite_url"].split("token=")[1]

        # Unactivated User が join（get_auth_info 依存なので is_activated 不要）
        app.dependency_overrides[deps.get_auth_info] = lambda: AuthInfo(
            uid=_UNACTIVATED_UID,
            email=_UNACTIVATED_EMAIL,
            display_name="Unactivated User",
        )
        r = e2e_client.post("/api/families/join", json={"token": token})
        assert r.status_code == 200

        # Firestore で is_activated: True を確認
        user_doc = firestore_client.collection("users").document(_UNACTIVATED_UID).get()
        assert user_doc.exists
        assert user_doc.to_dict().get("is_activated") is True

        # join 後は get_family_context を通じたアクセスが可能
        r = e2e_client.get("/api/families/me")
        assert r.status_code == 200

        # User1 に戻す
        app.dependency_overrides[deps.get_auth_info] = lambda: AuthInfo(
            uid=TEST_UID, email="e2e@example.com", display_name="E2E Test User"
        )

    def test_email_mismatch_returns_403(self, e2e_client):
        """招待 email とログイン email が不一致の場合 403 EMAIL_MISMATCH"""
        # User1 がファミリー作成 + 招待発行
        e2e_client.get("/api/families/me")
        r = e2e_client.post(
            "/api/families/invite",
            json={"email": "invited@example.com"},  # 別の email で招待
        )
        assert r.status_code == 201
        token = r.json()["invite_url"].split("token=")[1]

        # 別の email アカウントで join しようとする
        app.dependency_overrides[deps.get_auth_info] = lambda: AuthInfo(
            uid=_UNACTIVATED_UID,
            email=_UNACTIVATED_EMAIL,  # invited@example.com と不一致
            display_name="Unactivated User",
        )
        r = e2e_client.post("/api/families/join", json={"token": token})
        assert r.status_code == 403
        assert r.json()["detail"] == "EMAIL_MISMATCH"

        # User1 に戻す
        app.dependency_overrides[deps.get_auth_info] = lambda: AuthInfo(
            uid=TEST_UID, email="e2e@example.com", display_name="E2E Test User"
        )
