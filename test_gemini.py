#!/usr/bin/env python3
"""
Gemini Adapter の動作確認テスト

sample.pdf を解析して、構造化データを抽出する。
"""

import os
from dotenv import load_dotenv
from v2.adapters.credentials import get_google_credentials
from v2.adapters.google_sheets import GoogleSheetsConfigSource
from v2.adapters.gemini import GeminiDocumentAnalyzer

load_dotenv()

print("=" * 60)
print("Gemini Document Analyzer テスト")
print("=" * 60)

# 設定読み込み
project_id = os.getenv("PROJECT_ID")
spreadsheet_id = os.getenv("SPREADSHEET_ID")

if not project_id or not spreadsheet_id:
    print("❌ PROJECT_ID または SPREADSHEET_ID が設定されていません")
    exit(1)

# 認証
creds = get_google_credentials()

# Profiles/Rules読み込み
print("\n1. Google Sheetsから設定読み込み...")
config_source = GoogleSheetsConfigSource(creds, spreadsheet_id)
profiles = config_source.load_profiles()
rules = config_source.load_rules()
print(f"✅ Profiles: {len(profiles)}件, Rules: {len(rules)}件")

# Gemini初期化
print("\n2. Gemini初期化...")
analyzer = GeminiDocumentAnalyzer(
    credentials=creds,
    project_id=project_id,
    location="us-central1"
)
print("✅ Gemini初期化完了")

# サンプルPDF読み込み
pdf_path = "sample.pdf"
if not os.path.exists(pdf_path):
    print(f"❌ {pdf_path} が見つかりません")
    exit(1)

print(f"\n3. {pdf_path} を読み込み...")
with open(pdf_path, "rb") as f:
    content = f.read()
print(f"✅ ファイル読み込み完了: {len(content):,} bytes")

# Gemini解析実行
print("\n4. Gemini解析実行中...")
print("   (Gemini APIを呼び出しています。数秒かかります...)")

try:
    analysis = analyzer.analyze(
        content=content,
        mime_type="application/pdf",
        profiles=profiles,
        rules=rules,
    )

    print("\n" + "=" * 60)
    print("解析結果")
    print("=" * 60)

    print(f"\n📄 要約:")
    print(f"   {analysis.summary}")

    print(f"\n📂 カテゴリ: {analysis.category.value}")

    print(f"\n👥 関連プロファイル: {', '.join(analysis.related_profile_ids) or 'なし'}")

    print(f"\n📅 イベント: {len(analysis.events)}件")
    for i, event in enumerate(analysis.events, 1):
        print(f"   {i}. {event.summary}")
        print(f"      日時: {event.start} ～ {event.end}")
        print(f"      場所: {event.location or '(なし)'}")
        print(f"      信頼度: {event.confidence}")

    print(f"\n✅ タスク: {len(analysis.tasks)}件")
    for i, task in enumerate(analysis.tasks, 1):
        print(f"   {i}. {task.title}")
        print(f"      期限: {task.due_date}")
        print(f"      担当: {task.assignee}")

    print(f"\n📦 アーカイブ名: {analysis.archive_filename}")

    print("\n" + "=" * 60)
    print("✅ Gemini解析成功！")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ エラー: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
