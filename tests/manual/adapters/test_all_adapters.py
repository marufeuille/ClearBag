#!/usr/bin/env python3
"""
Adapter動作確認スクリプト

実際のAPIを呼び出すため、.envに以下の設定が必要:
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

使い方:
    # 全テスト
    uv run python test_adapters.py

    # Slackのみ
    uv run python test_adapters.py --slack
"""

import argparse
import os
import sys
from dotenv import load_dotenv

# .env読み込み
load_dotenv()


def test_slack():
    """Slack Adapter のテスト"""
    print("\n" + "=" * 60)
    print("Slack Adapter テスト")
    print("=" * 60)

    from v2.adapters.slack import SlackNotifier
    from v2.domain.models import TaskData, EventData

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("SLACK_CHANNEL_ID")

    if not bot_token or not channel_id:
        print("❌ SLACK_BOT_TOKEN または SLACK_CHANNEL_ID が設定されていません")
        return False

    try:
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
                note="Phase 3 動作確認テスト",
            )
        ]

        notifier.notify_file_processed(
            filename="test_phase3.pdf",
            summary="Phase 3 Adapter動作確認のテスト通知です。",
            events=events,
            tasks=tasks,
            file_link="https://example.com/test.pdf",
        )

        print("✅ Slack通知が送信されました")
        print(f"   チャンネル: {channel_id}")
        print("   → Slackアプリで確認してください")
        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_credentials():
    """Google認証情報のテスト"""
    print("\n" + "=" * 60)
    print("Google認証情報テスト")
    print("=" * 60)

    from v2.adapters.credentials import get_google_credentials

    try:
        creds = get_google_credentials()

        print(f"✅ 認証成功: {type(creds).__name__}")
        print(f"   Valid: {creds.valid}")

        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_google_sheets():
    """Google Sheets Adapter のテスト"""
    print("\n" + "=" * 60)
    print("Google Sheets Adapter テスト")
    print("=" * 60)

    from v2.adapters.credentials import get_google_credentials
    from v2.adapters.google_sheets import GoogleSheetsConfigSource

    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if not spreadsheet_id:
        print("❌ SPREADSHEET_ID が設定されていません")
        return False

    try:
        creds = get_google_credentials()
        config_source = GoogleSheetsConfigSource(creds, spreadsheet_id)

        # Profiles読み込み
        profiles = config_source.load_profiles()
        print(f"✅ Profiles読み込み成功: {len(profiles)}件")
        for profile_id, profile in list(profiles.items())[:3]:
            print(f"   - {profile_id}: {profile.name} ({profile.grade})")

        # Rules読み込み
        rules = config_source.load_rules()
        print(f"✅ Rules読み込み成功: {len(rules)}件")
        for rule in rules[:3]:
            print(f"   - {rule.rule_id}: {rule.rule_type}")

        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_google_drive():
    """Google Drive Adapter のテスト"""
    print("\n" + "=" * 60)
    print("Google Drive Adapter テスト")
    print("=" * 60)

    from v2.adapters.credentials import get_google_credentials
    from v2.adapters.google_drive import GoogleDriveStorage

    inbox_id = os.getenv("INBOX_FOLDER_ID")
    archive_id = os.getenv("ARCHIVE_FOLDER_ID")

    if not inbox_id or not archive_id:
        print("❌ INBOX_FOLDER_ID または ARCHIVE_FOLDER_ID が設定されていません")
        return False

    try:
        creds = get_google_credentials()
        storage = GoogleDriveStorage(creds, inbox_id, archive_id)

        # Inboxファイル一覧
        files = storage.list_inbox_files()
        print(f"✅ Inboxファイル一覧取得成功: {len(files)}件")
        for file_info in files[:3]:
            print(f"   - {file_info.name} ({file_info.mime_type})")

        if files:
            print(f"\n⚠️  注意: Inboxに{len(files)}個のファイルがあります")
            print("   download/archiveのテストは手動で実行してください")

        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_google_calendar():
    """Google Calendar Adapter のテスト"""
    print("\n" + "=" * 60)
    print("Google Calendar Adapter テスト")
    print("=" * 60)

    from v2.adapters.credentials import get_google_credentials
    from v2.adapters.google_calendar import GoogleCalendarService
    from v2.domain.models import EventData

    try:
        creds = get_google_credentials()
        calendar = GoogleCalendarService(creds)

        # テストイベント作成
        event = EventData(
            summary="[テスト] School Agent v2 Phase 3 動作確認",
            start="2026-02-20",
            end="2026-02-20",
            location="テスト",
            description="Phase 3のCalendar Adapter動作確認テストです。削除してOKです。",
        )

        event_url = calendar.create_event(
            calendar_id="primary",
            event=event,
            file_link="https://example.com/test.pdf"
        )

        print(f"✅ Calendarイベントが作成されました")
        print(f"   URL: {event_url}")
        print("   → Google Calendarで確認してください")

        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Adapter動作確認")
    parser.add_argument("--slack", action="store_true", help="Slackのみテスト")
    parser.add_argument("--creds", action="store_true", help="認証のみテスト")
    parser.add_argument("--sheets", action="store_true", help="Google Sheetsのみテスト")
    parser.add_argument("--drive", action="store_true", help="Google Driveのみテスト")
    parser.add_argument("--calendar", action="store_true", help="Google Calendarのみテスト")
    args = parser.parse_args()

    results = []

    # 個別指定がない場合は全テスト
    run_all = not (args.slack or args.creds or args.sheets or args.drive or args.calendar)

    if args.creds or run_all:
        results.append(("Credentials", test_credentials()))

    if args.sheets or run_all:
        results.append(("Google Sheets", test_google_sheets()))

    if args.drive or run_all:
        results.append(("Google Drive", test_google_drive()))

    if args.calendar or run_all:
        results.append(("Google Calendar", test_google_calendar()))

    if args.slack or run_all:
        results.append(("Slack", test_slack()))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")

    # 全て成功したか
    all_success = all(success for _, success in results)
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
