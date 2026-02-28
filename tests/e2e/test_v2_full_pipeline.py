#!/usr/bin/env python3
"""
v2アーキテクチャの統合テスト（End-to-End）

実際のInboxフォルダからファイルを取得し、全パイプラインを実行する。
- Google Sheetsから設定読み込み
- Google DriveのInboxからファイル取得
- Geminiで解析
- カレンダー/タスク登録
- Slack通知
- アーカイブ

警告: 実際のAPIを呼び出すため、Inboxにテスト用ファイルがある状態で実行してください。
"""

import logging

from v2.entrypoints.factory import create_orchestrator

# ログレベル設定（詳細表示）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

print("=" * 60)
print("School Agent v2 - End-to-End Integration Test")
print("=" * 60)

# Orchestrator生成
print("\n1. Creating orchestrator...")
orchestrator = create_orchestrator()
print("✅ Orchestrator created")

# 実行
print("\n2. Running full pipeline...")
print("   (This will process all files in Inbox)")
results = orchestrator.run()

# 結果表示
print("\n" + "=" * 60)
print("Results")
print("=" * 60)

if not results:
    print("\n✅ No files found in Inbox (nothing to process)")
else:
    print(f"\n📊 Processed {len(results)} file(s):\n")

    for i, result in enumerate(results, 1):
        print(f"[{i}] {result.file_info.name}")
        print(f"    File Link: {result.file_info.web_view_link}")

        if result.error:
            print(f"    ❌ Error: {result.error}")
            continue

        print(f"    📝 Summary: {result.analysis.summary}")
        print(f"    📂 Category: {result.analysis.category.value}")
        print(
            f"    👥 Related Profiles: {', '.join(result.analysis.related_profile_ids) or 'None'}"
        )

        print(f"\n    📅 Events Created: {result.events_created}")
        for j, event in enumerate(result.analysis.events, 1):
            print(f"       {j}. {event.summary}")
            print(f"          {event.start} - {event.end}")
            print(f"          Confidence: {event.confidence}")

        print(f"\n    ✅ Tasks Created: {result.tasks_created}")
        for j, task in enumerate(result.analysis.tasks, 1):
            print(f"       {j}. {task.title}")
            print(f"          Due: {task.due_date}")
            print(f"          Assignee: {task.assignee}")

        print(
            f"\n    📢 Notification Sent: {'Yes' if result.notification_sent else 'No'}"
        )
        print(f"    📦 Archived: {'Yes' if result.archived else 'No'}")
        if result.archived:
            print(f"    📦 Archive Name: {result.analysis.archive_filename}")

        print()

print("=" * 60)
errors = [r for r in results if r.error]
successes = [r for r in results if not r.error]

print(f"✅ Success: {len(successes)}")
print(f"❌ Errors: {len(errors)}")

if errors:
    print("\nFiles with errors:")
    for r in errors:
        print(f"  - {r.file_info.name}: {r.error}")

print("=" * 60)
print("✅ Integration test complete")
print("=" * 60)
