#!/usr/bin/env python3
"""
Profilesシートに設定されたカレンダーIDを使ってイベントを作成
"""

import os
from datetime import datetime

from dotenv import load_dotenv

from v2.adapters.credentials import get_google_credentials
from v2.adapters.google_calendar import GoogleCalendarService
from v2.adapters.google_sheets import GoogleSheetsConfigSource
from v2.domain.models import EventData

load_dotenv()

print("=" * 60)
print("Profilesのカレンダー設定を確認")
print("=" * 60)

# Google Sheetsから設定読み込み
creds = get_google_credentials()
spreadsheet_id = os.getenv("SPREADSHEET_ID")
config_source = GoogleSheetsConfigSource(creds, spreadsheet_id)

profiles = config_source.load_profiles()

print("\nProfilesのカレンダーID:")
for profile_id, profile in profiles.items():
    print(f"  {profile_id} ({profile.name}): {profile.calendar_id or '(未設定)'}")

# KOTAROのカレンダーにテストイベント作成
kotaro_profile = profiles.get("KOTARO")
if not kotaro_profile or not kotaro_profile.calendar_id:
    print("\n❌ KOTAROのカレンダーIDが設定されていません")
    exit(1)

calendar_id = kotaro_profile.calendar_id
print(f"\n使用するカレンダーID: {calendar_id}")

# イベント作成
calendar = GoogleCalendarService(creds)
today = datetime.now().strftime("%Y-%m-%d")

event = EventData(
    summary=f"[{kotaro_profile.name}] テスト遠足",
    start=today,
    end=today,
    location="動物園",
    description="Profilesシートに設定されたカレンダーへのテスト投稿です。",
)

print("\nイベント作成中...")
url = calendar.create_event(calendar_id, event, "https://example.com/test.pdf")
print(f"✅ 作成成功: {url}")
print(f"\n{kotaro_profile.name}のGoogle Calendarで確認してください！")
