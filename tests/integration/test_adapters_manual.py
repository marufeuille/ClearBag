"""
Adapter の手動動作確認テスト

実際のAPI呼び出しを行うため、pytest.mark.manual でスキップ。
手動実行時のみテストする。

実行方法:
    uv run pytest tests/integration/test_adapters_manual.py -v -m manual
"""

import pytest
import os
from dotenv import load_dotenv
from v2.domain.models import TaskData, EventData

# .envから環境変数読み込み
load_dotenv()


@pytest.mark.manual
@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN"),
    reason="SLACK_BOT_TOKEN not set"
)
class TestSlackAdapter:
    """Slack Adapter の動作確認"""

    def test_send_notification(self):
        """Slackに実際に通知を送信"""
        from v2.adapters.slack import SlackNotifier

        notifier = SlackNotifier(
            bot_token=os.getenv("SLACK_BOT_TOKEN"),
            channel_id=os.getenv("SLACK_CHANNEL_ID")
        )

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
class TestCredentials:
    """認証情報の取得テスト"""

    def test_get_credentials(self):
        """Google認証情報を取得"""
        from v2.adapters.credentials import get_google_credentials

        creds = get_google_credentials()

        assert creds is not None
        assert creds.valid

        print(f"✅ Google認証成功: {type(creds)}")
