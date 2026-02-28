"""Push サブスクリプション API の E2E テスト

Firestore Emulator を使ってサブスクリプション登録・削除を検証する。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

_SUBSCRIPTION_PAYLOAD = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/e2e-test-endpoint",
    "keys": {
        "auth": "e2e-auth-key",
        "p256dh": "e2e-p256dh-key",
    },
}


class TestPushSubscriptions:
    """POST /api/push-subscriptions, POST /api/push-subscriptions/unsubscribe のテスト"""

    def test_register_subscription(self, e2e_client, firestore_client):
        """サブスクリプションを登録し、Firestore に保存される"""
        r = e2e_client.post("/api/push-subscriptions", json=_SUBSCRIPTION_PAYLOAD)
        assert r.status_code == 204

        from tests.e2e.conftest import TEST_UID

        user_data = (
            firestore_client.collection("users").document(TEST_UID).get().to_dict()
        )
        assert user_data is not None
        sub = user_data.get("web_push_subscription")
        assert sub is not None
        assert sub["endpoint"] == _SUBSCRIPTION_PAYLOAD["endpoint"]
        assert sub["keys"]["auth"] == _SUBSCRIPTION_PAYLOAD["keys"]["auth"]
        assert sub["keys"]["p256dh"] == _SUBSCRIPTION_PAYLOAD["keys"]["p256dh"]

    def test_unregister_subscription(self, e2e_client, firestore_client):
        """登録後にアンサブスクライブすると web_push_subscription が削除される"""
        from tests.e2e.conftest import TEST_UID

        # まず登録
        e2e_client.post("/api/push-subscriptions", json=_SUBSCRIPTION_PAYLOAD)

        # 削除
        r = e2e_client.post("/api/push-subscriptions/unsubscribe")
        assert r.status_code == 204

        user_data = (
            firestore_client.collection("users").document(TEST_UID).get().to_dict()
        )
        assert user_data is not None
        assert "web_push_subscription" not in user_data

    def test_register_overwrites_existing_subscription(
        self, e2e_client, firestore_client
    ):
        """既存のサブスクリプションを新しいエンドポイントで上書きできる"""
        from tests.e2e.conftest import TEST_UID

        first_payload = {
            **_SUBSCRIPTION_PAYLOAD,
            "endpoint": "https://example.com/push/first",
        }
        second_payload = {
            **_SUBSCRIPTION_PAYLOAD,
            "endpoint": "https://example.com/push/second",
        }

        e2e_client.post("/api/push-subscriptions", json=first_payload)
        e2e_client.post("/api/push-subscriptions", json=second_payload)

        user_data = (
            firestore_client.collection("users").document(TEST_UID).get().to_dict()
        )
        assert (
            user_data["web_push_subscription"]["endpoint"] == second_payload["endpoint"]
        )
