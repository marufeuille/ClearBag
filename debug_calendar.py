#!/usr/bin/env python3
"""
Calendarの動作デバッグスクリプト

作成されたイベントを確認し、どのカレンダーに登録されているかを調べる。
"""

from dotenv import load_dotenv
from v2.adapters.credentials import get_google_credentials
from googleapiclient.discovery import build

load_dotenv()


def list_calendars():
    """利用可能なカレンダー一覧を表示"""
    print("=" * 60)
    print("利用可能なカレンダー一覧")
    print("=" * 60)

    creds = get_google_credentials()
    service = build('calendar', 'v3', credentials=creds)

    calendars = service.calendarList().list().execute()

    for calendar in calendars.get('items', []):
        print(f"\nカレンダー: {calendar['summary']}")
        print(f"  ID: {calendar['id']}")
        print(f"  Primary: {calendar.get('primary', False)}")
        print(f"  Access Role: {calendar['accessRole']}")


def list_recent_events(calendar_id='primary', max_results=10):
    """最近のイベントを表示"""
    print("\n" + "=" * 60)
    print(f"最近のイベント (calendar_id={calendar_id})")
    print("=" * 60)

    creds = get_google_credentials()
    service = build('calendar', 'v3', credentials=creds)

    try:
        events = service.events().list(
            calendarId=calendar_id,
            maxResults=max_results,
            orderBy='startTime',
            singleEvents=True,
            timeMin='2026-02-01T00:00:00Z',  # 2026年2月以降
            timeMax='2027-01-01T00:00:00Z'   # 2027年まで
        ).execute()

        items = events.get('items', [])
        if not items:
            print("イベントが見つかりませんでした")
        else:
            for event in items:
                start = event.get('start', {}).get('date') or event.get('start', {}).get('dateTime')
                print(f"\n- {event.get('summary', 'No Title')}")
                print(f"  開始: {start}")
                print(f"  URL: {event.get('htmlLink')}")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()


def search_test_events():
    """テストイベントを検索"""
    print("\n" + "=" * 60)
    print("テストイベントを検索")
    print("=" * 60)

    creds = get_google_credentials()
    service = build('calendar', 'v3', credentials=creds)

    # 全カレンダーを調べる
    calendars = service.calendarList().list().execute()

    for calendar in calendars.get('items', []):
        calendar_id = calendar['id']
        print(f"\n📅 {calendar['summary']} ({calendar_id})")

        try:
            events = service.events().list(
                calendarId=calendar_id,
                q='School Agent v2',  # テストイベントを検索
                maxResults=5,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            items = events.get('items', [])
            if items:
                for event in items:
                    start = event.get('start', {}).get('date') or event.get('start', {}).get('dateTime')
                    print(f"  ✅ 見つかった: {event.get('summary')}")
                    print(f"     開始: {start}")
                    print(f"     URL: {event.get('htmlLink')}")
            else:
                print(f"  テストイベントなし")

        except Exception as e:
            print(f"  ⚠️  アクセスできません: {e}")


if __name__ == "__main__":
    list_calendars()
    print("\n\n")
    list_recent_events('primary')
    print("\n\n")
    search_test_events()
