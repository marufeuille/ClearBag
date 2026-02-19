"""ActionDispatcher のテスト"""

from unittest.mock import MagicMock, call

import pytest

from v2.domain.models import Category, DocumentAnalysis, EventData, FileInfo, Profile, TaskData
from v2.services.action_dispatcher import ActionDispatcher, DispatchResult


class TestActionDispatcher:
    """ActionDispatcher の単体テスト"""

    def test_dispatch_filters_low_confidence_events(
        self, mock_calendar, mock_task_service, mock_notifier, sample_file_info
    ):
        """LOW confidence のイベントはカレンダーに登録されない"""
        # Arrange
        high_event = EventData(
            summary="遠足", start="2026-04-25", end="2026-04-25", confidence="HIGH"
        )
        low_event = EventData(
            summary="メモ", start="2026-04-26", end="2026-04-26", confidence="LOW"
        )
        analysis = DocumentAnalysis(
            summary="テスト",
            category=Category.EVENT,
            events=[high_event, low_event],
        )
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)

        # Act
        result = dispatcher.dispatch(sample_file_info, analysis, {})

        # Assert
        assert result.events_created == 1
        assert mock_calendar.create_event.call_count == 1
        # HIGH confidenceのイベントのみ登録されている
        mock_calendar.create_event.assert_called_once_with(
            "primary", high_event, sample_file_info.web_view_link
        )

    def test_dispatch_resolves_calendar_id_from_profile(
        self, mock_calendar, mock_task_service, mock_notifier, sample_file_info, sample_profiles
    ):
        """related_profile_ids からカレンダーIDが正しく解決される"""
        # Arrange
        event = EventData(summary="イベント", start="2026-04-25", end="2026-04-25")
        analysis = DocumentAnalysis(
            summary="テスト",
            category=Category.EVENT,
            related_profile_ids=["CHILD1"],
            events=[event],
        )
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)

        # Act
        dispatcher.dispatch(sample_file_info, analysis, sample_profiles)

        # Assert
        mock_calendar.create_event.assert_called_once_with(
            "calendar_child1@example.com",  # CHILD1 の calendar_id
            event,
            sample_file_info.web_view_link,
        )

    def test_dispatch_fallback_to_primary_when_profile_not_found(
        self, mock_calendar, mock_task_service, mock_notifier, sample_file_info
    ):
        """Profileが見つからない場合は primary にフォールバック"""
        # Arrange
        event = EventData(summary="イベント", start="2026-04-25", end="2026-04-25")
        analysis = DocumentAnalysis(
            summary="テスト",
            category=Category.EVENT,
            related_profile_ids=["UNKNOWN_ID"],
            events=[event],
        )
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)

        # Act
        dispatcher.dispatch(sample_file_info, analysis, {})

        # Assert
        mock_calendar.create_event.assert_called_once_with(
            "primary", event, sample_file_info.web_view_link
        )

    def test_dispatch_creates_all_tasks(
        self, mock_calendar, mock_task_service, mock_notifier, sample_file_info
    ):
        """全てのタスクがTaskServiceに登録される"""
        # Arrange
        task1 = TaskData(title="タスク1", due_date="2026-04-20")
        task2 = TaskData(title="タスク2", due_date="2026-04-21")
        analysis = DocumentAnalysis(
            summary="テスト",
            category=Category.TASK,
            tasks=[task1, task2],
        )
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)

        # Act
        result = dispatcher.dispatch(sample_file_info, analysis, {})

        # Assert
        assert result.tasks_created == 2
        assert mock_task_service.create_task.call_count == 2
        mock_task_service.create_task.assert_has_calls(
            [
                call(task1, sample_file_info.web_view_link),
                call(task2, sample_file_info.web_view_link),
            ],
            any_order=True,
        )

    def test_dispatch_sends_notification(
        self, mock_calendar, mock_task_service, mock_notifier, sample_file_info
    ):
        """通知が送信される"""
        # Arrange
        event = EventData(summary="イベント", start="2026-04-25", end="2026-04-25")
        task = TaskData(title="タスク", due_date="2026-04-20")
        analysis = DocumentAnalysis(
            summary="テスト文書",
            category=Category.EVENT,
            events=[event],
            tasks=[task],
        )
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)

        # Act
        result = dispatcher.dispatch(sample_file_info, analysis, {})

        # Assert
        assert result.notification_sent is True
        mock_notifier.notify_file_processed.assert_called_once_with(
            filename=sample_file_info.name,
            summary="テスト文書",
            events=[event],  # HIGH confidenceのみ
            tasks=[task],
            file_link=sample_file_info.web_view_link,
        )

    def test_dispatch_with_no_events_or_tasks(
        self, mock_calendar, mock_task_service, mock_notifier, sample_file_info
    ):
        """イベントもタスクもない場合でも通知は送信される"""
        # Arrange
        analysis = DocumentAnalysis(
            summary="情報のみの文書",
            category=Category.INFO,
        )
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)

        # Act
        result = dispatcher.dispatch(sample_file_info, analysis, {})

        # Assert
        assert result.events_created == 0
        assert result.tasks_created == 0
        assert result.notification_sent is True
        assert mock_calendar.create_event.call_count == 0
        assert mock_task_service.create_task.call_count == 0
        mock_notifier.notify_file_processed.assert_called_once()


class TestResolveCalendarId:
    """_resolve_calendar_id の静的メソッドテスト"""

    def test_resolve_first_matching_profile(self):
        """最初にマッチしたProfileのcalendar_idを返す"""
        profiles = {
            "CHILD1": Profile(
                id="CHILD1",
                name="太郎",
                grade="小3",
                keywords="",
                calendar_id="cal1",
            ),
            "CHILD2": Profile(
                id="CHILD2",
                name="花子",
                grade="小1",
                keywords="",
                calendar_id="cal2",
            ),
        }
        result = ActionDispatcher._resolve_calendar_id(["CHILD2", "CHILD1"], profiles)
        assert result == "cal2"  # CHILD2 が先にマッチ

    def test_resolve_fallback_to_primary(self):
        """マッチするProfileがない場合はprimaryを返す"""
        result = ActionDispatcher._resolve_calendar_id(["UNKNOWN"], {})
        assert result == "primary"

    def test_resolve_empty_related_ids(self):
        """related_idsが空の場合はprimaryを返す"""
        result = ActionDispatcher._resolve_calendar_id([], {})
        assert result == "primary"

    def test_resolve_skip_profile_with_empty_calendar_id(self):
        """calendar_idが空のProfileはスキップされる"""
        profiles = {
            "CHILD1": Profile(id="CHILD1", name="太郎", grade="小3", keywords="", calendar_id=""),
            "CHILD2": Profile(
                id="CHILD2",
                name="花子",
                grade="小1",
                keywords="",
                calendar_id="cal2",
            ),
        }
        result = ActionDispatcher._resolve_calendar_id(["CHILD1", "CHILD2"], profiles)
        assert result == "cal2"  # CHILD1はcalendar_idが空なのでスキップ
