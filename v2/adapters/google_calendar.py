"""Google Calendar Service Adapter

CalendarService ABCの実装。
既存 src/calendar_client.py を移植し、ABCに準拠。
"""

import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from v2.domain.models import EventData
from v2.domain.ports import CalendarService

logger = logging.getLogger(__name__)


class GoogleCalendarService(CalendarService):
    """
    Google Calendarを使ったイベント管理実装。

    終日イベント（YYYY-MM-DD）と時刻指定イベント（ISO8601）の両方に対応。
    """

    def __init__(self, credentials: Credentials, timezone: str = "Asia/Tokyo"):
        """
        Args:
            credentials: Google API認証情報
            timezone: タイムゾーン（デフォルト: Asia/Tokyo）
        """
        if not credentials:
            raise ValueError("credentials is required")

        self._service = build("calendar", "v3", credentials=credentials)
        self._timezone = timezone

    def create_event(self, calendar_id: str, event: EventData, file_link: str = "") -> str:
        """
        Google Calendarにイベントを作成。

        Args:
            calendar_id: カレンダーID（例: 'primary' or 'c_xxx@group.calendar.google.com'）
            event: イベントデータ
            file_link: 元ファイルへのリンク

        Returns:
            str: 作成されたイベントのURL

        Raises:
            Exception: イベント作成に失敗した場合
        """
        try:
            # 開始・終了時刻の処理
            start_body = self._build_datetime_body(event.start)
            end_body = self._build_datetime_body(event.end)

            # Descriptionにファイルリンクを追加
            description = event.description
            if file_link:
                description += f"\n\nOriginal File: {file_link}"

            # イベントボディ構築
            event_body = {
                "summary": event.summary or "No Title",
                "location": event.location,
                "description": description,
                "start": start_body,
                "end": end_body,
            }

            # Calendar API呼び出し
            created_event = (
                self._service.events().insert(calendarId=calendar_id, body=event_body).execute()
            )

            event_url: str = created_event.get("htmlLink", "")
            logger.info("Created calendar event: %s (%s)", event.summary, event_url)
            return event_url

        except Exception:
            logger.exception("Failed to create calendar event: %s", event.summary)
            raise

    def _build_datetime_body(self, datetime_str: str) -> dict:
        """
        日時文字列からCalendar APIのbodyを構築。

        Args:
            datetime_str: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS 形式

        Returns:
            dict: {'date': ...} or {'dateTime': ..., 'timeZone': ...}
        """
        if len(datetime_str) == 10:
            # 終日イベント（YYYY-MM-DD）
            return {"date": datetime_str}
        else:
            # 時刻指定イベント（ISO8601）
            return {"dateTime": datetime_str, "timeZone": self._timezone}
