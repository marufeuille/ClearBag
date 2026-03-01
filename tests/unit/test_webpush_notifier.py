"""WebPushNotifier のユニットテスト

pywebpush の webpush() 関数をモックして、各メソッドの
通知内容・スキップ条件を検証する。
"""

from unittest.mock import MagicMock, patch

import pytest
from v2.adapters.webpush_notifier import PushSubscription, VapidConfig, WebPushNotifier

_VAPID = VapidConfig(
    private_key="fake-private-key",
    public_key="fake-public-key",
    claims_email="test@example.com",
)

_SUB = PushSubscription(
    endpoint="https://fcm.googleapis.com/fcm/send/test",
    keys={"auth": "auth-key", "p256dh": "p256dh-key"},
)


@pytest.fixture
def notifier():
    return WebPushNotifier(_VAPID)


class TestNotifyAnalysisComplete:
    def test_sends_push_with_correct_payload(self, notifier):
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_analysis_complete(_SUB, "学校だより.pdf", "doc-123")

        mock_wp.assert_called_once()
        call_kwargs = mock_wp.call_args.kwargs
        import json

        payload = json.loads(call_kwargs["data"])
        assert payload["title"] == "解析完了"
        assert "学校だより.pdf" in payload["body"]
        assert payload["url"] == "/documents/doc-123"
        assert payload["tag"] == "analysis-complete-doc-123"


class TestNotifyMorningDigest:
    def test_sends_push_with_event_and_task_counts(self, notifier):
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_morning_digest(_SUB, event_count=3, task_count=2)

        mock_wp.assert_called_once()
        import json

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        assert payload["title"] == "ClearBag ダイジェスト"
        assert "3" in payload["body"]
        assert "2" in payload["body"]
        assert payload["url"] == "/calendar"
        assert payload["tag"] == "morning-digest"

    def test_sends_with_only_events(self, notifier):
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_morning_digest(_SUB, event_count=5, task_count=0)

        mock_wp.assert_called_once()
        import json

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        assert "5" in payload["body"]
        assert "タスク" not in payload["body"]

    def test_sends_with_only_tasks(self, notifier):
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_morning_digest(_SUB, event_count=0, task_count=4)

        mock_wp.assert_called_once()
        import json

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        assert "4" in payload["body"]

    def test_skips_when_no_events_or_tasks(self, notifier):
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_morning_digest(_SUB, event_count=0, task_count=0)

        mock_wp.assert_not_called()


class TestNotifyEventReminder:
    def test_sends_push_with_event_count(self, notifier):
        events = [MagicMock(), MagicMock(), MagicMock()]
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_event_reminder(_SUB, events)

        mock_wp.assert_called_once()
        import json

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        assert payload["title"] == "明日の予定リマインダー"
        assert "3" in payload["body"]
        assert payload["url"] == "/calendar"
        assert payload["tag"] == "event-reminder"

    def test_skips_when_no_events(self, notifier):
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_event_reminder(_SUB, [])

        mock_wp.assert_not_called()
