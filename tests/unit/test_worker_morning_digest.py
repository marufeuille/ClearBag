"""Worker 朝ダイジェストエンドポイントのユニットテスト

VAPID_PRIVATE_KEY 未設定時のスキップ、WebPush 送信ロジック、
410 Gone 時のサブスクリプション自動削除を検証する。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from v2.entrypoints.api.app import app
from v2.entrypoints.api.worker_auth import verify_worker_token


@pytest.fixture
def worker_client():
    """verify_worker_token をバイパスした TestClient"""
    app.dependency_overrides[verify_worker_token] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestMorningDigestEndpoint:
    def test_skips_when_no_vapid_key(self, worker_client):
        with patch.dict("os.environ", {}, clear=True):
            # VAPID_PRIVATE_KEY を環境変数から除く
            import os

            os.environ.pop("VAPID_PRIVATE_KEY", None)
            r = worker_client.post("/worker/morning-digest")

        assert r.status_code == 200
        assert r.json()["status"] == "skipped"
        assert r.json()["reason"] == "no_vapid_key"

    def test_sends_to_users_with_web_push_enabled(self, worker_client):
        """web_push=True かつ subscription があるユーザーに送信する"""
        user_with_push = {
            "notification_preferences": {"web_push": True},
            "web_push_subscription": {
                "endpoint": "https://fcm.example.com/push/user1",
                "keys": {"auth": "auth1", "p256dh": "p256dh1"},
            },
            "family_id": "family-1",
        }
        user_without_push = {
            "notification_preferences": {"web_push": False},
            "family_id": "family-1",
        }

        mock_user_doc_1 = MagicMock()
        mock_user_doc_1.id = "uid-1"
        mock_user_doc_1.to_dict.return_value = user_with_push

        mock_user_doc_2 = MagicMock()
        mock_user_doc_2.id = "uid-2"
        mock_user_doc_2.to_dict.return_value = user_without_push

        mock_db = MagicMock()
        mock_db.collection("users").stream.return_value = [
            mock_user_doc_1,
            mock_user_doc_2,
        ]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_events.return_value = [MagicMock()]
        mock_doc_repo.list_tasks.return_value = []

        mock_notifier = MagicMock()

        with (
            patch("v2.entrypoints.worker._ensure_firebase_init"),
            patch(
                "os.environ.get",
                side_effect=lambda k, d="": (
                    "fake-key" if k == "VAPID_PRIVATE_KEY" else d
                ),
            ),
            patch("v2.entrypoints.worker.firestore.Client", return_value=mock_db),
            patch(
                "v2.entrypoints.worker.FirestoreDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "v2.adapters.webpush_notifier.WebPushNotifier",
                return_value=mock_notifier,
            ),
        ):
            r = worker_client.post("/worker/morning-digest")

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["sent"] == 1  # uid-1 のみ送信
        assert data["errors"] == 0

    def test_removes_subscription_on_410(self, worker_client):
        """410 Gone エラー時に Firestore からサブスクリプションを削除する"""
        from pywebpush import WebPushException

        mock_response = MagicMock()
        mock_response.status_code = 410

        user_data = {
            "notification_preferences": {"web_push": True},
            "web_push_subscription": {
                "endpoint": "https://fcm.example.com/push/expired",
                "keys": {"auth": "auth", "p256dh": "p256dh"},
            },
            "family_id": "family-1",
        }

        mock_user_doc = MagicMock()
        mock_user_doc.id = "uid-expired"
        mock_user_doc.to_dict.return_value = user_data

        mock_db = MagicMock()
        mock_db.collection("users").stream.return_value = [mock_user_doc]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_events.return_value = [MagicMock()]
        mock_doc_repo.list_tasks.return_value = []

        gone_error = WebPushException("Gone")
        gone_error.response = mock_response

        mock_notifier = MagicMock()
        mock_notifier.notify_morning_digest.side_effect = gone_error

        with (
            patch("v2.entrypoints.worker._ensure_firebase_init"),
            patch(
                "os.environ.get",
                side_effect=lambda k, d="": (
                    "fake-key" if k == "VAPID_PRIVATE_KEY" else d
                ),
            ),
            patch("v2.entrypoints.worker.firestore.Client", return_value=mock_db),
            patch(
                "v2.entrypoints.worker.FirestoreDocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "v2.adapters.webpush_notifier.WebPushNotifier",
                return_value=mock_notifier,
            ),
        ):
            r = worker_client.post("/worker/morning-digest")

        assert r.status_code == 200
        data = r.json()
        assert data["errors"] == 1
        # Firestore の update が呼ばれたことを確認（DELETE_FIELD で削除）
        mock_db.collection("users").document("uid-expired").update.assert_called_once()
