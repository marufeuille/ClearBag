"""iCal Feed Renderer Adapter

CalendarFeedRenderer ABC の icalendar ライブラリを使った実装。
EventData のリストから RFC 5545 準拠の iCal 形式文字列を生成する。

出力例:
  BEGIN:VCALENDAR
  VERSION:2.0
  PRODID:-//ClearBag//ClearBag//JA
  ...
  BEGIN:VEVENT
  ...
  END:VEVENT
  END:VCALENDAR
"""

from __future__ import annotations

import logging
from datetime import datetime

from icalendar import Calendar, Event, vText

from v2.domain.models import EventData
from v2.domain.ports import CalendarFeedRenderer

logger = logging.getLogger(__name__)

_PRODID = "-//ClearBag//ClearBag//JA"
_DATE_FMT = "%Y-%m-%d"
_DATETIME_FMT = "%Y-%m-%dT%H:%M:%S"


class ICalRenderer(CalendarFeedRenderer):
    """
    icalendar ライブラリを使った iCal フィード生成実装。

    EventData の start/end が日付のみ（YYYY-MM-DD）の場合は
    終日イベント（DATE 型）として出力し、時刻付き（ISO8601）の場合は
    DATETIME 型として出力する。
    """

    def render(self, events: list[EventData]) -> str:
        """
        EventData リストから iCal 形式の文字列を生成。

        Args:
            events: 出力するイベントのリスト

        Returns:
            RFC 5545 準拠の iCal 文字列（Content-Type: text/calendar）
        """
        cal = Calendar()
        cal.add("prodid", _PRODID)
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", vText("ClearBag"))
        cal.add("x-wr-timezone", vText("Asia/Tokyo"))

        for event_data in events:
            vevent = self._build_vevent(event_data)
            cal.add_component(vevent)

        result = cal.to_ical().decode("utf-8")
        logger.info("Rendered iCal: events=%d, bytes=%d", len(events), len(result))
        return result

    @staticmethod
    def _parse_dt(value: str) -> datetime | str:
        """
        ISO8601 文字列を datetime または date 文字列にパース。

        時刻なし（YYYY-MM-DD）の場合は DATE 型として扱うため文字列を返す。
        """
        if "T" in value:
            return datetime.strptime(value, _DATETIME_FMT)
        return value  # 終日イベント（YYYY-MM-DD）

    @classmethod
    def _build_vevent(cls, event_data: EventData) -> Event:
        """EventData から VEVENT コンポーネントを構築"""
        vevent = Event()
        vevent.add("summary", event_data.summary)

        start = cls._parse_dt(event_data.start)
        end = cls._parse_dt(event_data.end)

        if isinstance(start, datetime):
            vevent.add("dtstart", start)
            vevent.add("dtend", end)
        else:
            # 終日イベント：DATE 型として追加
            from datetime import date as date_type

            vevent.add("dtstart", date_type.fromisoformat(start))
            vevent.add("dtend", date_type.fromisoformat(end))

        if event_data.location:
            vevent.add("location", event_data.location)
        if event_data.description:
            vevent.add("description", event_data.description)

        return vevent
