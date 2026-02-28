"""Push サブスクリプション API の E2E テスト

Firestore Emulator を使ってサブスクリプション登録・削除を検証する。
"""

from __future__ import annotations

import hashlib

import pytest

pytestmark = pytest.mark.e2e

_SUBSCRIPTION_PAYLOAD = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/e2e-test-endpoint",
    "keys": {
        "auth": "e2e-auth-key",
        "p256dh": "e2e-p256dh-key",
    },
}


def _endpoint_key(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode()).hexdigest()[:16]


class TestPushSubscriptions:
    """POST /api/push-subscriptions, POST /api/push-subscriptions/unsubscribe のテスト"""

    def test_register_subscription(self, e2e_client, firestore_client):
        """サブスクリプションを登録し、Firestore の web_push_subscriptions Map に保存される"""
        r = e2e_client.post("/api/push-subscriptions", json=_SUBSCRIPTION_PAYLOAD)
        assert r.status_code == 204

        from tests.e2e.conftest import TEST_UID

        user_data = (
            firestore_client.collection("users").document(TEST_UID).get().to_dict()
        )
        assert user_data is not None
        subscriptions = user_data.get("web_push_subscriptions")
        assert subscriptions is not None
        key = _endpoint_key(_SUBSCRIPTION_PAYLOAD["endpoint"])
        assert key in subscriptions
        sub = subscriptions[key]
        assert sub["endpoint"] == _SUBSCRIPTION_PAYLOAD["endpoint"]
        assert sub["keys"]["auth"] == _SUBSCRIPTION_PAYLOAD["keys"]["auth"]
        assert sub["keys"]["p256dh"] == _SUBSCRIPTION_PAYLOAD["keys"]["p256dh"]

    def test_unregister_subscription(self, e2e_client, firestore_client):
        """登録後にアンサブスクライブすると該当端末の subscription のみ削除される"""
        from tests.e2e.conftest import TEST_UID

        # まず登録
        e2e_client.post("/api/push-subscriptions", json=_SUBSCRIPTION_PAYLOAD)

        # 削除（endpoint を body に含める）
        r = e2e_client.post(
            "/api/push-subscriptions/unsubscribe",
            json={"endpoint": _SUBSCRIPTION_PAYLOAD["endpoint"]},
        )
        assert r.status_code == 204

        user_data = (
            firestore_client.collection("users").document(TEST_UID).get().to_dict()
        )
        assert user_data is not None
        subscriptions = user_data.get("web_push_subscriptions") or {}
        key = _endpoint_key(_SUBSCRIPTION_PAYLOAD["endpoint"])
        assert key not in subscriptions

    def test_multiple_devices_keep_independent_subscriptions(
        self, e2e_client, firestore_client
    ):
        """複数端末の subscription を登録し、それぞれ独立して管理される"""
        from tests.e2e.conftest import TEST_UID

        first_payload = {
            **_SUBSCRIPTION_PAYLOAD,
            "endpoint": "https://example.com/push/device-1",
        }
        second_payload = {
            **_SUBSCRIPTION_PAYLOAD,
            "endpoint": "https://example.com/push/device-2",
        }

        e2e_client.post("/api/push-subscriptions", json=first_payload)
        e2e_client.post("/api/push-subscriptions", json=second_payload)

        user_data = (
            firestore_client.collection("users").document(TEST_UID).get().to_dict()
        )
        subscriptions = user_data.get("web_push_subscriptions") or {}
        key1 = _endpoint_key(first_payload["endpoint"])
        key2 = _endpoint_key(second_payload["endpoint"])
        # 両方の端末のサブスクリプションが独立して保存される
        assert key1 in subscriptions
        assert key2 in subscriptions
        assert subscriptions[key1]["endpoint"] == first_payload["endpoint"]
        assert subscriptions[key2]["endpoint"] == second_payload["endpoint"]

    def test_unregister_one_device_keeps_other(self, e2e_client, firestore_client):
        """1台を削除しても他の端末の subscription は残る"""
        from tests.e2e.conftest import TEST_UID

        first_payload = {
            **_SUBSCRIPTION_PAYLOAD,
            "endpoint": "https://example.com/push/keep-device",
        }
        second_payload = {
            **_SUBSCRIPTION_PAYLOAD,
            "endpoint": "https://example.com/push/remove-device",
        }

        e2e_client.post("/api/push-subscriptions", json=first_payload)
        e2e_client.post("/api/push-subscriptions", json=second_payload)

        # 2台目のみ削除
        r = e2e_client.post(
            "/api/push-subscriptions/unsubscribe",
            json={"endpoint": second_payload["endpoint"]},
        )
        assert r.status_code == 204

        user_data = (
            firestore_client.collection("users").document(TEST_UID).get().to_dict()
        )
        subscriptions = user_data.get("web_push_subscriptions") or {}
        key1 = _endpoint_key(first_payload["endpoint"])
        key2 = _endpoint_key(second_payload["endpoint"])
        assert key1 in subscriptions  # 1台目は残る
        assert key2 not in subscriptions  # 2台目は削除
