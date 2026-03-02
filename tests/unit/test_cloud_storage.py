"""GCSBlobStorage.generate_signed_url() のユニットテスト

コードパス:
  1. エミュレーター環境 (STORAGE_EMULATOR_HOST 設定) → 直接 URL
  2. Cloud Run 環境 (SERVICE_ACCOUNT_EMAIL 設定) → IAM signBlob API
     2a. credentials が期限切れ → refresh() が呼ばれる
     2b. credentials が有効 → refresh() はスキップ
  3. ローカルデフォルト (いずれも未設定) → service_account_email なしで署名
"""

from unittest.mock import MagicMock, patch

from google.cloud import storage as gcs


def _make_storage(bucket_name: str = "test-bucket") -> tuple:
    """GCSBlobStorage と mock bucket を返すヘルパー。"""
    mock_client = MagicMock(spec=gcs.Client)
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    # import を遅延させてモックが先に効くようにする
    from v2.adapters.cloud_storage import GCSBlobStorage

    storage_adapter = GCSBlobStorage(bucket_name=bucket_name, client=mock_client)
    return storage_adapter, mock_bucket


class TestGenerateSignedUrlEmulator:
    def test_returns_direct_url(self, monkeypatch):
        """STORAGE_EMULATOR_HOST が設定されている場合は直接 URL を返す。"""
        monkeypatch.setenv("STORAGE_EMULATOR_HOST", "http://localhost:4443")
        monkeypatch.delenv("SERVICE_ACCOUNT_EMAIL", raising=False)

        storage_adapter, mock_bucket = _make_storage()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        url = storage_adapter.generate_signed_url("uploads/uid/doc.pdf")

        assert url == (
            "http://localhost:4443/storage/v1/b/test-bucket"
            "/o/uploads%2Fuid%2Fdoc.pdf?alt=media"
        )
        mock_blob.generate_signed_url.assert_not_called()


class TestGenerateSignedUrlCloudRun:
    def test_passes_service_account_email_and_token(self, monkeypatch):
        """SERVICE_ACCOUNT_EMAIL が設定されている場合は IAM signBlob API を使う。"""
        monkeypatch.delenv("STORAGE_EMULATOR_HOST", raising=False)
        monkeypatch.setenv("SERVICE_ACCOUNT_EMAIL", "sa@project.iam.gserviceaccount.com")

        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials.token = "fake-access-token"

        storage_adapter, mock_bucket = _make_storage()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://signed.url/path"

        with patch("google.auth.default", return_value=(mock_credentials, "project-id")):
            url = storage_adapter.generate_signed_url("uploads/uid/doc.pdf")

        assert url == "https://signed.url/path"
        _, kwargs = mock_blob.generate_signed_url.call_args
        assert kwargs["service_account_email"] == "sa@project.iam.gserviceaccount.com"
        assert kwargs["access_token"] == "fake-access-token"
        assert kwargs["version"] == "v4"
        assert kwargs["method"] == "GET"

    def test_refreshes_expired_credentials(self, monkeypatch):
        """credentials が期限切れの場合は refresh() を呼ぶ。"""
        monkeypatch.delenv("STORAGE_EMULATOR_HOST", raising=False)
        monkeypatch.setenv("SERVICE_ACCOUNT_EMAIL", "sa@project.iam.gserviceaccount.com")

        mock_credentials = MagicMock()
        mock_credentials.valid = False
        mock_credentials.token = "refreshed-token"

        storage_adapter, mock_bucket = _make_storage()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://signed.url/path"

        with (
            patch("google.auth.default", return_value=(mock_credentials, "project-id")),
            patch("google.auth.transport.requests.Request") as mock_request_cls,
        ):
            storage_adapter.generate_signed_url("uploads/uid/doc.pdf")

        mock_credentials.refresh.assert_called_once_with(mock_request_cls.return_value)

    def test_skips_refresh_for_valid_credentials(self, monkeypatch):
        """credentials が有効な場合は refresh() を呼ばない。"""
        monkeypatch.delenv("STORAGE_EMULATOR_HOST", raising=False)
        monkeypatch.setenv("SERVICE_ACCOUNT_EMAIL", "sa@project.iam.gserviceaccount.com")

        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials.token = "valid-token"

        storage_adapter, mock_bucket = _make_storage()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://signed.url/path"

        with patch("google.auth.default", return_value=(mock_credentials, "project-id")):
            storage_adapter.generate_signed_url("uploads/uid/doc.pdf")

        mock_credentials.refresh.assert_not_called()


class TestGenerateSignedUrlLocal:
    def test_no_service_account_email_in_kwargs(self, monkeypatch):
        """SERVICE_ACCOUNT_EMAIL 未設定の場合は service_account_email を渡さない。"""
        monkeypatch.delenv("STORAGE_EMULATOR_HOST", raising=False)
        monkeypatch.delenv("SERVICE_ACCOUNT_EMAIL", raising=False)

        storage_adapter, mock_bucket = _make_storage()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://signed.url/local"

        url = storage_adapter.generate_signed_url("uploads/uid/doc.pdf")

        assert url == "https://signed.url/local"
        _, kwargs = mock_blob.generate_signed_url.call_args
        assert "service_account_email" not in kwargs
        assert "access_token" not in kwargs
