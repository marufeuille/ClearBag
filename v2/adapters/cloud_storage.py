"""Cloud Storage Adapter

BlobStorage ABC の Google Cloud Storage 実装。
ユーザーがアップロードしたファイルの保存・取得・削除を行う。
"""

from __future__ import annotations

import datetime
import logging
import os

import google.auth
from google.auth.transport import requests as auth_requests
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

    def delete_by_prefix(self, prefix: str) -> None:
        """指定プレフィックス配下の全ファイルを一括削除"""
        blobs = list(self._client.list_blobs(self._bucket_name, prefix=prefix))
        if not blobs:
            logger.info("No blobs found for prefix: %s", prefix)
            return
        for blob in blobs:
            blob.delete()
        logger.info(
            "Deleted %d blobs with prefix: bucket=%s, prefix=%s",
            len(blobs),
            self._bucket_name,
            prefix,
        )

    def generate_signed_url(self, blob_path: str, expiration_minutes: int = 15) -> str:
        """
        GCS オブジェクトへの一時的な署名付き URL を生成する。

        GCS エミュレーター環境では signed URL 非対応のため直接 URL を返す。
        本番環境では V4 署名（HMAC-SHA256）を使用する。

        Args:
            blob_path: GCS 上のパス
            expiration_minutes: URL の有効期限（分、デフォルト 15）

        Returns:
            ダウンロード用の一時 URL
        """
        blob = self._bucket.blob(blob_path)
        emulator_host = os.environ.get("STORAGE_EMULATOR_HOST")
        if emulator_host:
            # エミュレーターは signed URL 非対応 → 直接アクセス URL を返す
            encoded_path = blob_path.replace("/", "%2F")
            return f"{emulator_host}/storage/v1/b/{self._bucket_name}/o/{encoded_path}?alt=media"

        signing_kwargs: dict[str, str] = {}
        sa_email = os.environ.get("SERVICE_ACCOUNT_EMAIL")
        if sa_email:
            # Cloud Run: compute_engine.Credentials はローカル秘密鍵を持たないため
            # IAM signBlob API を使うよう service_account_email + access_token を渡す
            credentials, _ = google.auth.default()
            if not credentials.valid:
                credentials.refresh(auth_requests.Request())
            signing_kwargs["service_account_email"] = sa_email
            signing_kwargs["access_token"] = credentials.token

        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiration_minutes),
            method="GET",
            **signing_kwargs,
        )
        logger.info(
            "Generated signed URL: bucket=%s, path=%s, expires=%dm",
            self._bucket_name,
            blob_path,
            expiration_minutes,
        )
        return url
