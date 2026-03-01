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
        """後方互換: events/tasks なしは旧形式のbodyを返す"""
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

    def test_rich_body_with_summary_and_events_tasks(self, notifier):
        """events/tasks を渡すとリッチ形式のbodyが生成される"""
        import json
        from types import SimpleNamespace

        events = [SimpleNamespace(summary="[長男] 遠足", start="2025-10-25T08:30:00")]
        tasks = [SimpleNamespace(title="同意書の提出", due_date="2025-10-20")]

        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_analysis_complete(
                _SUB,
                "20251025_遠足_長男.pdf",
                "doc-456",
                summary="遠足のお知らせです。",
                events=events,
                tasks=tasks,
            )

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        body = payload["body"]
        assert "20251025_遠足_長男.pdf" in body
        assert "遠足のお知らせです。" in body
        assert "[長男] 遠足" in body
        assert "2025-10-25" in body
        assert "同意書の提出" in body
        assert "2025-10-20" in body

    def test_body_truncated_at_200_chars(self, notifier):
        """200文字を超えるbodyは '...' で切り詰められる"""
        import json

        long_summary = "あ" * 300
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_analysis_complete(
                _SUB,
                "file.pdf",
                "doc-789",
                summary=long_summary,
                events=[],
                tasks=[],
            )

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        body = payload["body"]
        assert len(body) <= 200
        assert body.endswith("...")

    def test_remaining_count_shown_when_more_than_3(self, notifier):
        """イベント・タスクが3件超のとき「他 N件」が表示される"""
        import json
        from types import SimpleNamespace

        events = [
            SimpleNamespace(summary=f"イベント{i}", start="2025-10-25")
            for i in range(5)
        ]
        tasks = [
            SimpleNamespace(title=f"タスク{i}", due_date="2025-10-20")
            for i in range(4)
        ]

        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_analysis_complete(
                _SUB, "file.pdf", "doc-999", events=events, tasks=tasks
            )

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        assert "他 3件" in payload["body"]  # (5-3) + (4-3) = 3


class TestNotifyMorningDigest:
    def test_sends_push_with_event_and_task_counts(self, notifier):
        """後方互換: events/tasks なしは件数ベースのbodyを返す"""
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

    def test_rich_body_with_events_and_tasks_lists(self, notifier):
        """events/tasks リストを渡すとリッチ形式のbodyが生成される"""
        import json
        from types import SimpleNamespace

        events = [SimpleNamespace(summary="[長男] 保護者会", start="2025-03-07")]
        tasks = [SimpleNamespace(title="集金袋", due_date="2025-03-03")]

        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_morning_digest(
                _SUB, event_count=1, task_count=1, events=events, tasks=tasks
            )

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        body = payload["body"]
        assert "[長男] 保護者会" in body
        assert "2025-03-07" in body
        assert "集金袋" in body
        assert "2025-03-03" in body
        # 旧形式の「今週の」は含まれないこと
        assert "今週の" not in body

    def test_digest_body_remaining_count(self, notifier):
        """4件以上のイベントは「他 N件」で省略される"""
        import json
        from types import SimpleNamespace

        events = [
            SimpleNamespace(summary=f"イベント{i}", start="2025-03-0{i+1}")
            for i in range(4)
        ]

        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_morning_digest(
                _SUB, event_count=4, task_count=0, events=events, tasks=[]
            )

        payload = json.loads(mock_wp.call_args.kwargs["data"])
        assert "他 1件" in payload["body"]


class TestWebpushCallParameters:
    def test_content_encoding_and_ttl_are_passed(self, notifier):
        """content_encoding と ttl が webpush() に渡されることを検証"""
        with patch("v2.adapters.webpush_notifier.webpush") as mock_wp:
            notifier.notify_analysis_complete(_SUB, "file.pdf", "doc-001")

        call_kwargs = mock_wp.call_args.kwargs
        assert call_kwargs["content_encoding"] == "aes128gcm"
        assert call_kwargs["ttl"] == 86400


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
