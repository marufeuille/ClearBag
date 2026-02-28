"""Push サブスクリプション API のユニットテスト

POST /api/push-subscriptions             → サブスクリプション登録
POST /api/push-subscriptions/unsubscribe → サブスクリプション削除
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import (
    FamilyContext,
    get_family_context,
    get_user_config_repo,
)

_UID = "test-uid"
_FAMILY_ID = "test-family-id"
_CTX = FamilyContext(uid=_UID, family_id=_FAMILY_ID, role="owner")

_SUBSCRIPTION_PAYLOAD = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
    "keys": {
        "auth": "test-auth-key",
        "p256dh": "test-p256dh-key",
    },
}


@pytest.fixture
def mock_user_repo():
    repo = MagicMock()
    repo.get_user.return_value = {}
    return repo


@pytest.fixture
def client(mock_user_repo):
    app.dependency_overrides[get_family_context] = lambda: _CTX
    app.dependency_overrides[get_user_config_repo] = lambda: mock_user_repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestRegisterPushSubscription:
    def test_register_saves_subscription_to_firestore(self, client, mock_user_repo):
        # Act
        r = client.post("/api/push-subscriptions", json=_SUBSCRIPTION_PAYLOAD)

        # Assert
        assert r.status_code == 204
        mock_user_repo.update_user.assert_called_once_with(
            _UID,
            {
                "web_push_subscription": {
                    "endpoint": _SUBSCRIPTION_PAYLOAD["endpoint"],
                    "keys": _SUBSCRIPTION_PAYLOAD["keys"],
                }
            },
        )

    def test_register_missing_endpoint_returns_422(self, client):
        r = client.post(
            "/api/push-subscriptions", json={"keys": {"auth": "a", "p256dh": "b"}}
        )
        assert r.status_code == 422

    def test_register_missing_keys_returns_422(self, client):
        r = client.post(
            "/api/push-subscriptions",
            json={"endpoint": "https://example.com/push"},
        )
        assert r.status_code == 422


class TestUnregisterPushSubscription:
    def test_unregister_removes_subscription_from_firestore(
        self, client, mock_user_repo
    ):
        # Act
        r = client.post("/api/push-subscriptions/unsubscribe")

        # Assert
        assert r.status_code == 204
        # DELETE_FIELD sentinel が渡されることを確認（型チェックは省略）
        assert mock_user_repo.update_user.call_count == 1
        call_args = mock_user_repo.update_user.call_args
        assert call_args[0][0] == _UID
        assert "web_push_subscription" in call_args[0][1]
