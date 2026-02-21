"""Factory - 依存性注入の組み立て

全AdapterとServiceを組み立て、Orchestratorを生成する。
"""

import logging
from v2.config import AppConfig
from v2.adapters.credentials import get_google_credentials
from v2.adapters.google_sheets import GoogleSheetsConfigSource
from v2.adapters.google_drive import GoogleDriveStorage
from v2.adapters.gemini import GeminiDocumentAnalyzer
from v2.adapters.google_calendar import GoogleCalendarService
from v2.adapters.slack import SlackNotifier
from v2.domain.ports import TaskService, Notifier
from v2.domain.models import TaskData, EventData
from v2.services.action_dispatcher import ActionDispatcher
from v2.services.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def create_orchestrator(config: AppConfig | None = None) -> Orchestrator:
    """
    Orchestratorを生成（全依存を組み立て）。

    Args:
        config: アプリケーション設定（Noneの場合は環境変数から読み込み）

    Returns:
        Orchestrator: 実行可能なオーケストレータ

    Raises:
        ValueError: 必須設定が不足している場合
    """
    if config is None:
        config = AppConfig.from_env()

    logger.info("Creating orchestrator with config: project_id=%s", config.project_id)

    # 1. Google認証
    logger.info("Initializing Google credentials...")
    creds = get_google_credentials()

    # 2. Adapters生成
    logger.info("Creating adapters...")

    config_source = GoogleSheetsConfigSource(
        credentials=creds,
        spreadsheet_id=config.spreadsheet_id,
    )

    file_storage = GoogleDriveStorage(
        credentials=creds,
        inbox_folder_id=config.inbox_folder_id,
        archive_folder_id=config.archive_folder_id,
    )

    analyzer = GeminiDocumentAnalyzer(
        credentials=creds,
        project_id=config.project_id,
        location=config.vertex_ai_location,
        model_name=config.gemini_model,
    )

    calendar_service = GoogleCalendarService(credentials=creds)

    # Slackはオプショナル（トークンがない場合はスキップ可能）
    task_service = _NullTaskService()

    notifier = None
    if config.slack_bot_token and config.slack_channel_id:
        notifier = SlackNotifier(
            bot_token=config.slack_bot_token,
            channel_id=config.slack_channel_id,
        )
        logger.info("Slack notifier enabled")
    else:
        logger.warning("Slack tokens not set, notifications will not be sent")

    # 3. ActionDispatcher生成（task_service/notifierがNoneでも動作）
    action_dispatcher = ActionDispatcher(
        calendar=calendar_service,
        task_service=task_service,
        notifier=notifier or _NullNotifier(),
    )

    # 4. Orchestrator生成
    orchestrator = Orchestrator(
        config_source=config_source,
        file_storage=file_storage,
        analyzer=analyzer,
        action_dispatcher=action_dispatcher,
    )

    logger.info("Orchestrator created successfully")
    return orchestrator


# Null Object Pattern（Todoist/Slackが無効な場合の代替）

class _NullTaskService(TaskService):
    """TaskServiceのNull Object（何もしない）"""
    def create_task(self, task: TaskData, file_link: str = "") -> str:
        logger.debug("NullTaskService: task skipped (Todoist not configured)")
        return "null"


class _NullNotifier(Notifier):
    """NotifierのNull Object（何もしない）"""
    def notify_file_processed(
        self,
        filename: str,
        summary: str,
        events: list[EventData],
        tasks: list[TaskData],
        file_link: str = "",
    ) -> None:
        logger.debug("NullNotifier: notification skipped (Slack not configured)")
