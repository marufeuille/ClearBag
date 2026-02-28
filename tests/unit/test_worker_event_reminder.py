"""Worker イベントリマインダーエンドポイントのユニットテスト

VAPID_PRIVATE_KEY 未設定時のスキップ、翌日イベントがあるユーザーのみへの送信、
イベントなしユーザーのスキップ、410 Gone 時の自動削除を検証する。
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from v2.entrypoints.api.app import app
from v2.entrypoints.api.worker_auth import verify_worker_token


@pytest.fixture
def worker_client():
    app.dependency_overrides[verify_worker_token] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _sub_key(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode()).hexdigest()[:16]


class TestEventReminderEndpoint:
    def test_skips_when_no_vapid_key(self, worker_client):
        import os

        os.environ.pop("VAPID_PRIVATE_KEY", None)
        with patch.dict("os.environ", {}, clear=True):
            r = worker_client.post("/worker/event-reminder")

        assert r.status_code == 200
        assert r.json()["status"] == "skipped"
        assert r.json()["reason"] == "no_vapid_key"

    def test_sends_only_to_users_with_tomorrow_events(self, worker_client):
        """翌日のイベントがあるユーザーにのみ送信する"""
        endpoint1 = "https://fcm.example.com/push/u1"
        endpoint2 = "https://fcm.example.com/push/u2"
        user_with_events = {
            "notification_preferences": {"web_push": True},
            "web_push_subscriptions": {
                _sub_key(endpoint1): {
                    "endpoint": endpoint1,
                    "keys": {"auth": "a", "p256dh": "p"},
                }
            },
            "family_id": "fam-1",
        }
        user_no_events = {
            "notification_preferences": {"web_push": True},
            "web_push_subscriptions": {
                _sub_key(endpoint2): {
                    "endpoint": endpoint2,
                    "keys": {"auth": "b", "p256dh": "q"},
                }
            },
            "family_id": "fam-2",
        }

        mock_doc1 = MagicMock()
        mock_doc1.id = "uid-1"
        mock_doc1.to_dict.return_value = user_with_events

        mock_doc2 = MagicMock()
        mock_doc2.id = "uid-2"
        mock_doc2.to_dict.return_value = user_no_events

        mock_db = MagicMock()
        mock_db.collection("users").stream.return_value = [mock_doc1, mock_doc2]

        mock_doc_repo = MagicMock()
        # fam-1 には翌日のイベントあり、fam-2 はなし
        mock_doc_repo.list_events.side_effect = lambda fid, **kw: (
            [MagicMock()] if fid == "fam-1" else []
        )

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
            r = worker_client.post("/worker/event-reminder")

        assert r.status_code == 200
        data = r.json()
        assert data["sent"] == 1  # uid-1 のみ送信
        assert data["errors"] == 0
        mock_notifier.notify_event_reminder.assert_called_once()

    def test_removes_subscription_on_410(self, worker_client):
        """410 Gone 時に Firestore から該当端末のサブスクリプションを削除する"""
        from pywebpush import WebPushException

        mock_response = MagicMock()
        mock_response.status_code = 410

        endpoint = "https://expired.example.com/push"
        sub_key = _sub_key(endpoint)
        user_data = {
            "notification_preferences": {"web_push": True},
            "web_push_subscriptions": {
                sub_key: {
                    "endpoint": endpoint,
                    "keys": {"auth": "a", "p256dh": "p"},
                }
            },
            "family_id": "fam-1",
        }

        mock_doc = MagicMock()
        mock_doc.id = "uid-expired"
        mock_doc.to_dict.return_value = user_data

        mock_db = MagicMock()
        mock_db.collection("users").stream.return_value = [mock_doc]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_events.return_value = [MagicMock()]

        gone_error = WebPushException("Gone")
        gone_error.response = mock_response

        mock_notifier = MagicMock()
        mock_notifier.notify_event_reminder.side_effect = gone_error

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
            r = worker_client.post("/worker/event-reminder")

        assert r.status_code == 200
        assert r.json()["errors"] == 1
        # Firestore の update が呼ばれ、該当端末キーのみ DELETE_FIELD で削除される
        update_call = mock_db.collection("users").document("uid-expired").update
        update_call.assert_called_once()
        updated_field = list(update_call.call_args[0][0].keys())[0]
        assert updated_field == f"web_push_subscriptions.{sub_key}"
