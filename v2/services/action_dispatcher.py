"""ActionDispatcher - 解析結果からアクション実行への振り分け"""

from __future__ import annotations
from dataclasses import dataclass
import logging
from v2.domain.models import DocumentAnalysis, FileInfo, Profile
from v2.domain.ports import CalendarService, TaskService, Notifier

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    """アクション実行結果"""
    events_created: int = 0
    tasks_created: int = 0
    notification_sent: bool = False


class ActionDispatcher:
    """
    DocumentAnalysisの結果に基づいて各サービスへアクションを振り分ける。

    既存core.pyのL68-111の責務を再設計。
    - LOW confidenceイベントの除外
    - Calendar IDの解決
    - Calendar/Todoist/Slackへの振り分け
    """

    def __init__(
        self,
        calendar: CalendarService,
        task_service: TaskService,
        notifier: Notifier,
    ) -> None:
        self._calendar = calendar
        self._task_service = task_service
        self._notifier = notifier

    def dispatch(
        self,
        file_info: FileInfo,
        analysis: DocumentAnalysis,
        profiles: dict[str, Profile],
    ) -> DispatchResult:
        """
        解析結果に基づいてアクションを実行。

        Args:
            file_info: ファイル情報
            analysis: Geminiによる解析結果
            profiles: プロファイル辞書（Calendar ID解決用）

        Returns:
            DispatchResult: 実行結果サマリー
        """
        result = DispatchResult()

        # Calendar events (LOW confidence は除外)
        eligible_events = [
            e for e in analysis.events if e.confidence != "LOW"
        ]
        logger.info(
            "Processing %d events (%d filtered by confidence)",
            len(eligible_events),
            len(analysis.events) - len(eligible_events),
        )

        for event in eligible_events:
            calendar_id = self._resolve_calendar_id(
                analysis.related_profile_ids, profiles
            )
            logger.debug(
                "Creating event '%s' on calendar %s", event.summary, calendar_id
            )
            self._calendar.create_event(
                calendar_id, event, file_info.web_view_link
            )
            result.events_created += 1

        # Tasks
        logger.info("Processing %d tasks", len(analysis.tasks))
        for task in analysis.tasks:
            logger.debug("Creating task '%s'", task.title)
            self._task_service.create_task(task, file_info.web_view_link)
            result.tasks_created += 1

        # Notification
        logger.info("Sending notification")
        self._notifier.notify_file_processed(
            filename=file_info.name,
            summary=analysis.summary,
            events=eligible_events,
            tasks=analysis.tasks,
            file_link=file_info.web_view_link,
        )
        result.notification_sent = True

        return result

    @staticmethod
    def _resolve_calendar_id(
        related_ids: list[str], profiles: dict[str, Profile]
    ) -> str:
        """
        ProfileIDのリストからカレンダーIDを解決。

        related_idsの最初のIDに対応するProfileのcalendar_idを返す。
        見つからない場合は "primary" にフォールバック。

        Args:
            related_ids: 関連するProfile IDのリスト
            profiles: Profile ID -> Profile の辞書

        Returns:
            calendar_id: Google Calendar ID
        """
        for pid in related_ids:
            if pid in profiles and profiles[pid].calendar_id:
                return profiles[pid].calendar_id
        return "primary"
