"""v2/adapters/credentials.py のユニットテスト"""

from v2.adapters.credentials import _is_cloud_environment, get_google_credentials


class TestIsCloudEnvironment:
    """_is_cloud_environment() の環境変数検出テスト"""

    def test_returns_true_when_k_service_is_set(self, monkeypatch):
        """Cloud Run Services の環境変数で True を返す"""
        monkeypatch.setenv("K_SERVICE", "my-service")
        assert _is_cloud_environment() is True

    def test_returns_true_when_function_target_is_set(self, monkeypatch):
        """Cloud Functions の環境変数で True を返す"""
        monkeypatch.setenv("FUNCTION_TARGET", "my-function")
        assert _is_cloud_environment() is True

    def test_returns_true_when_cloud_run_job_is_set(self, monkeypatch):
        """Cloud Run Jobs の環境変数で True を返す"""
        monkeypatch.setenv("CLOUD_RUN_JOB", "my-job")
        assert _is_cloud_environment() is True

    def test_returns_false_when_no_cloud_env_vars_set(self, monkeypatch):
        """いずれの環境変数も未設定のときは False を返す"""
        monkeypatch.delenv("K_SERVICE", raising=False)
        monkeypatch.delenv("FUNCTION_TARGET", raising=False)
        monkeypatch.delenv("CLOUD_RUN_JOB", raising=False)
        assert _is_cloud_environment() is False


class TestGetGoogleCredentials:
    """get_google_credentials() がCloud環境でADCを使用することを確認"""

    def setup_method(self):
        """各テスト前にlru_cacheをクリア"""
        get_google_credentials.cache_clear()

    def teardown_method(self):
        """各テスト後にlru_cacheをクリア"""
        get_google_credentials.cache_clear()

    def test_uses_adc_in_cloud_run_job_environment(self, monkeypatch):
        """Cloud Run Jobs環境でADCを使用する（FileNotFoundErrorが発生しない）"""
        monkeypatch.setenv("CLOUD_RUN_JOB", "my-job")

        import unittest.mock as mock

        mock_creds = mock.MagicMock()
        with mock.patch(
            "google.auth.default", return_value=(mock_creds, "project-id")
        ) as mock_adc:
            result = get_google_credentials()
            mock_adc.assert_called_once()
            assert result is mock_creds

    def test_uses_adc_in_k_service_environment(self, monkeypatch):
        """Cloud Run Services環境でADCを使用する"""
        monkeypatch.setenv("K_SERVICE", "my-service")

        import unittest.mock as mock

        mock_creds = mock.MagicMock()
        with mock.patch(
            "google.auth.default", return_value=(mock_creds, "project-id")
        ) as mock_adc:
            result = get_google_credentials()
            mock_adc.assert_called_once()
            assert result is mock_creds
