#!/usr/bin/env python3
"""
今日の日付でカレンダーイベントを作成するテスト
"""

from datetime import datetime, timedelta

from dotenv import load_dotenv
from v2.adapters.credentials import get_google_credentials
from v2.adapters.google_calendar import GoogleCalendarService
from v2.domain.models import EventData

load_dotenv()

# 今日の日付
today = datetime.now().strftime("%Y-%m-%d")
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

print(f"今日の日付でイベント作成テスト: {today}")

creds = get_google_credentials()
calendar = GoogleCalendarService(creds)

# 終日イベント（今日）
event1 = EventData(
    summary="[テスト今日] School Agent v2 終日イベント",
    start=today,
    end=today,
    description="今日の日付で作成したテストイベントです。",
)

# 時刻指定イベント（明日）
tomorrow_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
event2 = EventData(
    summary="[テスト明日] School Agent v2 時刻指定イベント",
    start=tomorrow_time,
    end=(datetime.now() + timedelta(days=1, hours=1)).strftime("%Y-%m-%dT11:00:00"),
    description="明日10時のテストイベントです。",
)

print("\n1. 終日イベント作成...")
url1 = calendar.create_event("primary", event1, "https://example.com/test1.pdf")
print(f"✅ 作成成功: {url1}")

print("\n2. 時刻指定イベント作成...")
url2 = calendar.create_event("primary", event2, "https://example.com/test2.pdf")
print(f"✅ 作成成功: {url2}")

print("\n" + "=" * 60)
print("Google Calendarで確認してください:")
print(f"- 今日 ({today}): [テスト今日] School Agent v2 終日イベント")
print(f"- 明日 ({tomorrow} 10:00): [テスト明日] School Agent v2 時刻指定イベント")
print("=" * 60)
