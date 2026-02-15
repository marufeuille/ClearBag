"""Slack Notifier Adapter

Notifier ABCの実装。
既存 src/slack_client.py を移植し、ABCに準拠。
"""

import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from v2.domain.ports import Notifier
from v2.domain.models import EventData, TaskData

logger = logging.getLogger(__name__)


class SlackNotifier(Notifier):
    """
    Slack WebClientを使った通知実装。

    既存の問題点を修正:
    - 環境変数への直接依存を排除（コンストラクタで注入）
    - print → logging
    - エラーハンドリング改善
    """

    def __init__(self, bot_token: str, channel_id: str):
        """
        Args:
            bot_token: Slack Bot Token
            channel_id: デフォルトの通知先チャンネルID
        """
        if not bot_token:
            raise ValueError("bot_token is required")
        if not channel_id:
            raise ValueError("channel_id is required")

        self._client = WebClient(token=bot_token)
        self._channel_id = channel_id

    def notify_file_processed(
        self,
        filename: str,
        summary: str,
        events: list[EventData],
        tasks: list[TaskData],
        file_link: str = "",
    ) -> None:
        """
        ファイル処理完了を Slack に通知。

        Args:
            filename: 処理したファイル名
            summary: 文書要約
            events: 作成されたイベントのリスト
            tasks: 作成されたタスクのリスト
            file_link: 元ファイルへのリンク
        """
        message = self._build_message(filename, summary, events, tasks, file_link)

        try:
            response = self._client.chat_postMessage(
                channel=self._channel_id,
                text=message
            )
            logger.info(
                "Slack message sent: ts=%s, channel=%s",
                response['ts'],
                self._channel_id
            )
        except SlackApiError as e:
            logger.error(
                "Failed to send Slack message: %s", e.response['error']
            )
            raise  # 呼び出し元でエラーハンドリング

    def _build_message(
        self,
        filename: str,
        summary: str,
        events: list[EventData],
        tasks: list[TaskData],
        file_link: str,
    ) -> str:
        """
        Slackメッセージを組み立て（既存ロジックを移植）。

        Args:
            filename: ファイル名
            summary: 要約
            events: イベントリスト
            tasks: タスクリスト
            file_link: ファイルリンク

        Returns:
            str: フォーマットされたメッセージ
        """
        lines = [f"*Processed File:* {filename}"]

        if file_link:
            lines.append(f"*Link:* {file_link}")

        lines.append("")
        lines.append(f"*Summary:*\n{summary}")
        lines.append("")

        if events:
            lines.append("*Events Created:*")
            for event in events:
                lines.append(f"- {event.summary} ({event.start})")
            lines.append("")

        if tasks:
            lines.append("*Tasks Created:*")
            for task in tasks:
                lines.append(f"- {task.title} (Due: {task.due_date})")

        return "\n".join(lines)
