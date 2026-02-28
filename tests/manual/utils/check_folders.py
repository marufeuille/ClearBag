#!/usr/bin/env python3
"""
Inbox/Archiveフォルダの内容を確認する
"""

import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from v2.adapters.credentials import get_google_credentials

load_dotenv()

INBOX_FOLDER_ID = os.getenv("INBOX_FOLDER_ID")
ARCHIVE_FOLDER_ID = os.getenv("ARCHIVE_FOLDER_ID")

creds = get_google_credentials()
service = build("drive", "v3", credentials=creds)

print("=" * 60)
print("Drive Folders Status")
print("=" * 60)

# Inbox確認
print("\n📥 INBOX:")
results = (
    service.files()
    .list(
        q=f"'{INBOX_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name, mimeType, webViewLink)",
    )
    .execute()
)
inbox_files = results.get("files", [])
if inbox_files:
    for f in inbox_files:
        print(f"  - {f['name']} ({f['mimeType']})")
        print(f"    ID: {f['id']}")
else:
    print("  (empty)")

# Archive確認
print("\n📦 ARCHIVE:")
results = (
    service.files()
    .list(
        q=f"'{ARCHIVE_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name, mimeType, webViewLink)",
        pageSize=10,
    )
    .execute()
)
archive_files = results.get("files", [])
if archive_files:
    for f in archive_files[:5]:  # 最初の5件のみ表示
        print(f"  - {f['name']} ({f['mimeType']})")
        print(f"    ID: {f['id']}")
    if len(archive_files) > 5:
        print(f"  ... and {len(archive_files) - 5} more files")
else:
    print("  (empty)")

print("\n" + "=" * 60)
