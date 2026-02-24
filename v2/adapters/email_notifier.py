"""Email Notifier Adapter

SendGrid を使ったメール通知実装（Phase 3）。
解析完了時と朝のダイジェストメールに使用する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import sendgrid
from sendgrid.helpers.mail import Content, Email, Mail, To

from v2.domain.models import EventData, TaskData

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """メール送信の設定"""

    api_key: str
    from_email: str = "noreply@clearbag.app"
    from_name: str = "ClearBag"


class SendGridEmailNotifier:
    """
    SendGrid を使ったメール通知実装。

    MVP では解析完了通知のみ実装し、
    朝のダイジストメール（Cloud Scheduler 連携）は Phase 3 で追加する。
    """

    def __init__(self, config: EmailConfig) -> None:
        """
        Args:
            config: SendGrid API キーとフォームアドレスの設定
        """
        self._sg = sendgrid.SendGridAPIClient(api_key=config.api_key)
        self._from_email = Email(config.from_email, config.from_name)

    def notify_analysis_complete(
        self,
        to_email: str,
        original_filename: str,
        summary: str,
        events: list[EventData],
        tasks: list[TaskData],
    ) -> None:
        """
        解析完了メールを送信。

        Args:
            to_email: 送信先メールアドレス
            original_filename: 解析したファイル名
            summary: 文書の要約
            events: 抽出されたイベントリスト
            tasks: 抽出されたタスクリスト
        """
        subject = f"【ClearBag】{original_filename} の解析が完了しました"
        body = self._build_analysis_body(original_filename, summary, events, tasks)

        self._send(to_email, subject, body)

    def send_morning_digest(
        self,
        to_email: str,
        upcoming_events: list[EventData],
        pending_tasks: list[TaskData],
    ) -> None:
        """
        朝のダイジェストメールを送信（Cloud Scheduler から呼び出す）。

        Args:
            to_email: 送信先メールアドレス
            upcoming_events: 今後7日間のイベント
            pending_tasks: 未完了タスク
        """
        subject = "【ClearBag】今日のお知らせ"
        body = self._build_digest_body(upcoming_events, pending_tasks)
        self._send(to_email, subject, body)

    def _send(self, to_email: str, subject: str, body: str) -> None:
        """メールを送信する内部メソッド"""
        mail = Mail(
            from_email=self._from_email,
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", body),
        )
        try:
            response = self._sg.send(mail)
            logger.info(
                "Email sent: to=%s, subject=%s, status=%d",
                to_email,
                subject,
                response.status_code,
            )
        except Exception:
            logger.exception("Failed to send email: to=%s", to_email)
            raise

    @staticmethod
    def _build_analysis_body(
        filename: str,
        summary: str,
        events: list[EventData],
        tasks: list[TaskData],
    ) -> str:
        lines = [
            f"「{filename}」の解析が完了しました。",
            "",
            f"■ 要約\n{summary}",
            "",
        ]
        if events:
            lines.append("■ 登録されたイベント")
            for e in events:
                lines.append(f"  ・{e.summary} ({e.start})")
            lines.append("")
        if tasks:
            lines.append("■ 登録されたタスク")
            for t in tasks:
                lines.append(f"  ・{t.title} (期限: {t.due_date})")
            lines.append("")
        lines.append("ClearBag でご確認ください。")
        return "\n".join(lines)

    @staticmethod
    def _build_digest_body(
        events: list[EventData],
        tasks: list[TaskData],
    ) -> str:
        lines = ["おはようございます。今日のClearBagダイジェストです。", ""]
        if events:
            lines.append("■ 今後のイベント")
            for e in events:
                lines.append(f"  ・{e.summary} ({e.start})")
            lines.append("")
        if tasks:
            lines.append("■ 未完了タスク")
            for t in tasks:
                lines.append(f"  ・{t.title} (期限: {t.due_date})")
            lines.append("")
        if not events and not tasks:
            lines.append("今後の予定・タスクはありません。")
        return "\n".join(lines)
