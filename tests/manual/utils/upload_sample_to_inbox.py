#!/usr/bin/env python3
"""
sample.pdfをGoogle DriveのInboxフォルダにアップロードする

テスト用ユーティリティ。
"""

import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from v2.adapters.credentials import get_google_credentials

load_dotenv()

INBOX_FOLDER_ID = os.getenv("INBOX_FOLDER_ID")
if not INBOX_FOLDER_ID:
    print("❌ INBOX_FOLDER_ID not set")
    exit(1)

PDF_PATH = "sample.pdf"
if not os.path.exists(PDF_PATH):
    print(f"❌ {PDF_PATH} not found")
    exit(1)

print("=" * 60)
print("Upload sample.pdf to Inbox")
print("=" * 60)

# 認証
creds = get_google_credentials()
service = build("drive", "v3", credentials=creds)

# アップロード
file_metadata = {"name": "sample.pdf", "parents": [INBOX_FOLDER_ID]}

media = MediaFileUpload(PDF_PATH, mimetype="application/pdf", resumable=True)

print(f"\nUploading {PDF_PATH} to Inbox folder...")
file = (
    service.files()
    .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
    .execute()
)

print("✅ Uploaded successfully!")
print(f"   File ID: {file['id']}")
print(f"   Name: {file['name']}")
print(f"   Link: {file['webViewLink']}")
print("\n" + "=" * 60)
print("Ready to run: uv run python -m v2.entrypoints.cli")
print("=" * 60)
