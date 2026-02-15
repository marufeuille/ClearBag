"""設定管理 - 環境変数の型安全な読み込み"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    """アプリケーション設定"""
    project_id: str
    spreadsheet_id: str
    inbox_folder_id: str
    archive_folder_id: str
    todoist_token: str
    slack_bot_token: str
    slack_channel_id: str
    vertex_ai_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-pro"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """環境変数から設定を読み込む"""
        load_dotenv()

        project_id = os.getenv("PROJECT_ID")
        if not project_id:
            raise ValueError("PROJECT_ID is not set in environment")

        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID is not set in environment")

        inbox_folder_id = os.getenv("INBOX_FOLDER_ID")
        if not inbox_folder_id:
            raise ValueError("INBOX_FOLDER_ID is not set in environment")

        archive_folder_id = os.getenv("ARCHIVE_FOLDER_ID")
        if not archive_folder_id:
            raise ValueError("ARCHIVE_FOLDER_ID is not set in environment")

        todoist_token = os.getenv("TODOIST_API_TOKEN", "")
        slack_bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        slack_channel_id = os.getenv("SLACK_CHANNEL_ID", "")

        return cls(
            project_id=project_id,
            spreadsheet_id=spreadsheet_id,
            inbox_folder_id=inbox_folder_id,
            archive_folder_id=archive_folder_id,
            todoist_token=todoist_token,
            slack_bot_token=slack_bot_token,
            slack_channel_id=slack_channel_id,
            vertex_ai_location=os.getenv("VERTEX_AI_LOCATION", "us-central1"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
        )
