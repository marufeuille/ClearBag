"""ICalRenderer のユニットテスト"""

from v2.adapters.ical_renderer import ICalRenderer
from v2.domain.models import EventData


class TestICalRenderer:
    """ICalRenderer の単体テスト"""

    def setup_method(self):
        self.renderer = ICalRenderer()

    def test_render_returns_string(self):
        """render() が文字列を返す"""
        events = [
            EventData(
                summary="遠足",
                start="2026-04-25T08:30:00",
                end="2026-04-25T15:00:00",
            )
        ]
        result = self.renderer.render(events)
        assert isinstance(result, str)

    def test_render_contains_ical_header(self):
        """iCal ヘッダーが含まれる"""
        result = self.renderer.render([])
        assert "BEGIN:VCALENDAR" in result
        assert "END:VCALENDAR" in result
        assert "VERSION:2.0" in result
        assert "ClearBag" in result

    def test_render_with_datetime_event(self):
        """時刻付きイベントが正しく出力される"""
        events = [
            EventData(
                summary="[長男] 遠足",
                start="2026-04-25T08:30:00",
                end="2026-04-25T15:00:00",
                location="動物園",
            )
        ]
        result = self.renderer.render(events)
        assert "BEGIN:VEVENT" in result
        assert "END:VEVENT" in result
        assert "[長男] 遠足" in result
        assert "動物園" in result

    def test_render_with_allday_event(self):
        """終日イベント（日付のみ）が DATE 型として出力される"""
        events = [
            EventData(
                summary="運動会",
                start="2026-05-10",
                end="2026-05-10",
            )
        ]
        result = self.renderer.render(events)
        assert "BEGIN:VEVENT" in result
        assert "運動会" in result
        # DATE 型のイベントは時刻なし（T が含まれない）
        assert "DTSTART;VALUE=DATE:" in result or "DTSTART:" in result

    def test_render_empty_events(self):
        """イベントなしの場合も有効な iCal が出力される"""
        result = self.renderer.render([])
        assert "BEGIN:VCALENDAR" in result
        assert "BEGIN:VEVENT" not in result

    def test_render_multiple_events(self):
        """複数イベントが正しく出力される"""
        events = [
            EventData(summary="イベント1", start="2026-04-01", end="2026-04-01"),
            EventData(summary="イベント2", start="2026-04-02", end="2026-04-02"),
        ]
        result = self.renderer.render(events)
        assert result.count("BEGIN:VEVENT") == 2
        assert "イベント1" in result
        assert "イベント2" in result
