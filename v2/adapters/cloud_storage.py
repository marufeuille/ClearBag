"""Cloud Storage Adapter

BlobStorage ABC の Google Cloud Storage 実装。
ユーザーがアップロードしたファイルの保存・取得・削除を行う。
"""

from __future__ import annotations

import logging

from google.cloud import storage

from v2.domain.ports import BlobStorage

logger = logging.getLogger(__name__)


class GCSBlobStorage(BlobStorage):
    """
    Google Cloud Storage を使った BlobStorage 実装。

    全ファイルは単一バケット内の blob_path で管理する。
    パス規約: uploads/{uid}/{document_id}{ext}
    """

    def __init__(self, bucket_name: str, client: storage.Client | None = None) -> None:
        """
        Args:
            bucket_name: GCS バケット名
            client: 初期化済みの GCS クライアント（省略時は ADC で自動初期化）
        """
        self._client = client or storage.Client()
        self._bucket = self._client.bucket(bucket_name)
        self._bucket_name = bucket_name

    def upload(self, blob_path: str, content: bytes, content_type: str) -> str:
        """
        ファイルを GCS にアップロード。

        Args:
            blob_path: GCS 上のパス（例: "uploads/uid123/doc456.pdf"）
            content: バイナリ内容
            content_type: MIME タイプ（例: "application/pdf"）

        Returns:
            ストレージパス（blob_path と同一）
        """
        blob = self._bucket.blob(blob_path)
        blob.upload_from_string(content, content_type=content_type)
        logger.info(
            "Uploaded: bucket=%s, path=%s, size=%d bytes",
            self._bucket_name,
            blob_path,
            len(content),
        )
        return blob_path

    def download(self, blob_path: str) -> bytes:
        """
        GCS からファイルをダウンロード。

        Args:
            blob_path: GCS 上のパス

        Returns:
            ファイルのバイナリ内容

        Raises:
            google.cloud.exceptions.NotFound: ファイルが存在しない場合
        """
        blob = self._bucket.blob(blob_path)
        content = blob.download_as_bytes()
        logger.info(
            "Downloaded: bucket=%s, path=%s, size=%d bytes",
            self._bucket_name,
            blob_path,
            len(content),
        )
        return content

    def delete(self, blob_path: str) -> None:
        """
        GCS からファイルを削除。

        Args:
            blob_path: GCS 上のパス

        Note:
            ファイルが存在しない場合は警告ログを出力してスキップする。
        """
        blob = self._bucket.blob(blob_path)
        try:
            blob.delete()
            logger.info("Deleted: bucket=%s, path=%s", self._bucket_name, blob_path)
        except Exception:
            logger.warning(
                "Failed to delete (may not exist): bucket=%s, path=%s",
                self._bucket_name,
                blob_path,
            )
