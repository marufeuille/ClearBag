"""
Adapter の手動動作確認テスト

実際のAPI呼び出しを行うため、pytest.mark.manual でスキップ。
手動実行時のみテストする。

実行方法:
    uv run pytest tests/integration/test_adapters_manual.py -v -m manual
"""

import os

import pytest
from dotenv import load_dotenv

from v2.domain.models import EventData, TaskData

# .envから環境変数読み込み
load_dotenv()


@pytest.mark.manual
@pytest.mark.skipif(not os.getenv("SLACK_BOT_TOKEN"), reason="SLACK_BOT_TOKEN not set")
class TestSlackAdapter:
    """Slack Adapter の動作確認"""

    def test_send_notification(self):
        """Slackに実際に通知を送信"""
        from v2.adapters.slack import SlackNotifier

        bot_token = os.getenv("SLACK_BOT_TOKEN")
        channel_id = os.getenv("SLACK_CHANNEL_ID")
        assert bot_token is not None, "SLACK_BOT_TOKEN is required"
        assert channel_id is not None, "SLACK_CHANNEL_ID is required"

        notifier = SlackNotifier(bot_token=bot_token, channel_id=channel_id)

        # テストデータ
        events = [
            EventData(
                summary="[テスト] 遠足",
                start="2026-04-25T08:00:00",
                end="2026-04-25T15:00:00",
                location="動物園",
            )
        ]
        tasks = [
            TaskData(
                title="[テスト] 同意書の提出",
                due_date="2026-04-20",
                assignee="PARENT",
            )
        ]

        # 実行
        notifier.notify_file_processed(
            filename="test_file.pdf",
            summary="これはテスト通知です。",
            events=events,
            tasks=tasks,
            file_link="https://example.com/test.pdf",
        )

        print("✅ Slack通知が送信されました。Slackを確認してください。")


@pytest.mark.manual
@pytest.mark.skipif(not os.getenv("TODOIST_API_TOKEN"), reason="TODOIST_API_TOKEN not set")
class TestTodoistAdapter:
    """Todoist Adapter の動作確認"""

    def test_create_task(self):
        """Todoistに実際にタスクを作成"""
        from v2.adapters.todoist import TodoistAdapter

        api_token = os.getenv("TODOIST_API_TOKEN")
        assert api_token is not None, "TODOIST_API_TOKEN is required"

        adapter = TodoistAdapter(api_token=api_token)

        # テストタスク
        task = TaskData(
            title="[テスト] School Agent v2 動作確認",
            due_date="2026-02-20",
            assignee="PARENT",
            note="これはPhase 3の動作確認テストです。",
        )

        # 実行
        task_id = adapter.create_task(task, file_link="https://example.com/test.pdf")

        print(f"✅ Todoistタスクが作成されました: {task_id}")
        print("   Todoistアプリで確認してください。")


@pytest.mark.manual
class TestCredentials:
    """認証情報の取得テスト"""

    def test_get_credentials(self):
        """Google認証情報を取得"""
        from v2.adapters.credentials import get_google_credentials

        creds = get_google_credentials()

        assert creds is not None
        assert creds.valid

        print(f"✅ Google認証成功: {type(creds)}")
