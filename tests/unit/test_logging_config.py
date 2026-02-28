"""logging_config モジュールのテスト"""

import json
import logging
from unittest.mock import patch

from v2.logging_config import CloudLoggingFormatter, setup_logging


class TestCloudLoggingFormatter:
    """CloudLoggingFormatter の単体テスト"""

    def _make_record(
        self,
        message: str = "test message",
        level: int = logging.INFO,
        exc_info=None,
    ) -> logging.LogRecord:
        """テスト用の LogRecord を生成するヘルパー"""
        record = logging.LogRecord(
            name="test.logger",
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=exc_info,
        )
        return record

    def test_format_returns_valid_json(self):
        """フォーマット結果が有効なJSONであること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record("hello world")
        output = formatter.format(record)

        parsed = json.loads(output)
        assert parsed["message"] == "hello world"

    def test_severity_info(self):
        """INFO レベルが severity=INFO にマッピングされること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record(level=logging.INFO)
        parsed = json.loads(formatter.format(record))
        assert parsed["severity"] == "INFO"

    def test_severity_warning(self):
        """WARNING レベルが severity=WARNING にマッピングされること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record(level=logging.WARNING)
        parsed = json.loads(formatter.format(record))
        assert parsed["severity"] == "WARNING"

    def test_severity_error(self):
        """ERROR レベルが severity=ERROR にマッピングされること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record(level=logging.ERROR)
        parsed = json.loads(formatter.format(record))
        assert parsed["severity"] == "ERROR"

    def test_severity_debug(self):
        """DEBUG レベルが severity=DEBUG にマッピングされること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record(level=logging.DEBUG)
        parsed = json.loads(formatter.format(record))
        assert parsed["severity"] == "DEBUG"

    def test_severity_critical(self):
        """CRITICAL レベルが severity=CRITICAL にマッピングされること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record(level=logging.CRITICAL)
        parsed = json.loads(formatter.format(record))
        assert parsed["severity"] == "CRITICAL"

    def test_required_fields_present(self):
        """必須フィールド (severity, message, logger, timestamp) が含まれること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record()
        parsed = json.loads(formatter.format(record))

        assert "severity" in parsed
        assert "message" in parsed
        assert "logger" in parsed
        assert "timestamp" in parsed

    def test_logger_name(self):
        """logger フィールドにロガー名が設定されること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record()
        record.name = "v2.services.orchestrator"
        parsed = json.loads(formatter.format(record))
        assert parsed["logger"] == "v2.services.orchestrator"

    def test_exception_info_included(self):
        """例外情報が exception フィールドとして含まれること"""
        formatter = CloudLoggingFormatter()

        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = self._make_record(exc_info=exc_info)
        parsed = json.loads(formatter.format(record))

        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "test error" in parsed["exception"]

    def test_no_exception_field_when_no_exception(self):
        """例外情報がない場合、exception フィールドが含まれないこと"""
        formatter = CloudLoggingFormatter()
        record = self._make_record()
        parsed = json.loads(formatter.format(record))
        assert "exception" not in parsed

    def test_japanese_message_encoded_correctly(self):
        """日本語メッセージが正しくエンコードされること"""
        formatter = CloudLoggingFormatter()
        record = self._make_record("学校配布物を処理しました")
        output = formatter.format(record)

        # ensure_ascii=False なので日本語がそのまま含まれる
        assert "学校配布物を処理しました" in output
        parsed = json.loads(output)
        assert parsed["message"] == "学校配布物を処理しました"


class TestSetupLogging:
    """setup_logging() の動作テスト"""

    def test_uses_json_formatter_in_cloud_run_job_env(self):
        """CLOUD_RUN_JOB 環境変数がある場合、JSON フォーマッタが使われること"""
        with patch.dict(
            "os.environ", {"CLOUD_RUN_JOB": "school-agent-dev"}, clear=False
        ):
            setup_logging()

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0].formatter, CloudLoggingFormatter)

    def test_uses_json_formatter_in_k_service_env(self):
        """K_SERVICE 環境変数がある場合、JSON フォーマッタが使われること"""
        with patch.dict("os.environ", {"K_SERVICE": "my-service"}, clear=False):
            setup_logging()

        root_logger = logging.getLogger()
        assert isinstance(root_logger.handlers[0].formatter, CloudLoggingFormatter)

    def test_uses_text_formatter_in_local_env(self):
        """Cloud Run 環境変数がない場合、テキスト フォーマッタが使われること"""
        env_without_cloud = {
            k: v
            for k, v in __import__("os").environ.items()
            if k not in ("K_SERVICE", "CLOUD_RUN_JOB")
        }
        with patch.dict("os.environ", env_without_cloud, clear=True):
            setup_logging()

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
        assert not isinstance(root_logger.handlers[0].formatter, CloudLoggingFormatter)

    def test_log_level_respected(self):
        """LOG_LEVEL 環境変数が反映されること"""
        with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}, clear=False):
            setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_handlers_cleared_on_reinitialize(self):
        """setup_logging() を複数回呼んでもハンドラが重複しないこと"""
        setup_logging()
        setup_logging()

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
