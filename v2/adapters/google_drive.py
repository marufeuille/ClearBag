"""Google Drive File Storage Adapter

FileStorage ABCの実装。
既存 src/drive_utils.py を移植し、ABCに準拠。
"""

import io
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from v2.domain.ports import FileStorage
from v2.domain.models import FileInfo

logger = logging.getLogger(__name__)


class GoogleDriveStorage(FileStorage):
    """
    Google Driveを使ったファイルストレージ実装。

    Inbox/Archiveフォルダを管理し、ファイルの一覧取得・ダウンロード・移動を行う。
    """

    def __init__(
        self,
        credentials: Credentials,
        inbox_folder_id: str,
        archive_folder_id: str
    ):
        """
        Args:
            credentials: Google API認証情報
            inbox_folder_id: Inboxフォルダ（受信）のID
            archive_folder_id: Archiveフォルダ（処理済み）のID
        """
        if not credentials:
            raise ValueError("credentials is required")
        if not inbox_folder_id:
            raise ValueError("inbox_folder_id is required")
        if not archive_folder_id:
            raise ValueError("archive_folder_id is required")

        self._service = build('drive', 'v3', credentials=credentials)
        self._inbox_id = inbox_folder_id
        self._archive_id = archive_folder_id

    def list_inbox_files(self) -> list[FileInfo]:
        """
        Inboxフォルダ内のファイル一覧を取得。

        Returns:
            list[FileInfo]: ファイル情報のリスト

        Raises:
            Exception: Drive API呼び出しに失敗した場合
        """
        try:
            query = f"'{self._inbox_id}' in parents and trashed = false"
            logger.info("🔍 [Drive API] Listing files with query: %s", query)
            logger.info("🔍 [Drive API] Inbox folder ID: %s", self._inbox_id)

            results = self._service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, createdTime, modifiedTime)",
                pageSize=100
            ).execute()

            items = results.get('files', [])
            logger.info("📥 [Drive API] Raw response: %d files returned from API", len(items))

            if items:
                logger.info("📋 [Drive API] File details:")
                for item in items:
                    logger.info("  - ID: %s, Name: %s, MimeType: %s, Created: %s, Modified: %s",
                               item['id'], item['name'], item['mimeType'],
                               item.get('createdTime', 'N/A'), item.get('modifiedTime', 'N/A'))
            else:
                logger.warning("⚠️ [Drive API] No files found in Inbox. Possible reasons:")
                logger.warning("  1. Inbox folder is actually empty")
                logger.warning("  2. Service account lacks permission to the folder")
                logger.warning("  3. Files were added after the last sync/cache refresh")
                logger.warning("  4. Folder ID is incorrect: %s", self._inbox_id)

            file_infos = [
                FileInfo(
                    id=item['id'],
                    name=item['name'],
                    mime_type=item['mimeType'],
                    web_view_link=item.get('webViewLink', '')
                )
                for item in items
            ]

            logger.info("✅ [Drive API] Successfully created %d FileInfo objects", len(file_infos))
            return file_infos

        except Exception as e:
            logger.exception("❌ [Drive API] Failed to list files in Inbox folder")
            raise

    def download(self, file_id: str) -> bytes:
        """
        ファイルをダウンロード。

        Args:
            file_id: ファイルID

        Returns:
            bytes: ファイルの内容

        Raises:
            Exception: ダウンロードに失敗した場合
        """
        try:
            logger.info("⬇️ [Drive API] Starting download for file ID: %s", file_id)
            request = self._service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(
                        "Download progress: %d%%", int(status.progress() * 100)
                    )

            content = fh.getvalue()
            logger.info("✅ [Drive API] Downloaded file: %s (%d bytes)", file_id, len(content))
            return content

        except Exception as e:
            logger.exception("❌ [Drive API] Failed to download file: %s", file_id)
            raise

    def archive(self, file_id: str, new_name: str) -> None:
        """
        ファイルをリネームしてArchiveフォルダに移動。

        Args:
            file_id: ファイルID
            new_name: 新しいファイル名

        Raises:
            Exception: ファイル移動に失敗した場合
        """
        try:
            logger.info("📦 [Drive API] Starting archive process for file: %s", file_id)
            logger.info("📦 [Drive API] Target name: %s", new_name)

            # 1. 現在の親フォルダを取得
            file = self._service.files().get(
                fileId=file_id, fields='parents'
            ).execute()
            previous_parents = ",".join(file.get('parents', []))
            logger.info("📦 [Drive API] Current parents: %s", previous_parents)

            # 2. Archiveフォルダに移動 + リネーム
            self._service.files().update(
                fileId=file_id,
                addParents=self._archive_id,
                removeParents=previous_parents,
                body={'name': new_name},
                fields='id, parents'
            ).execute()

            logger.info(
                "✅ [Drive API] Archived file: %s -> %s (moved to %s)",
                file_id,
                new_name,
                self._archive_id
            )

        except Exception as e:
            logger.exception("❌ [Drive API] Failed to archive file: %s", file_id)
            raise
