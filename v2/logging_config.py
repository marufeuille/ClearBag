"""ロギング設定モジュール

Cloud Run / Cloud Logging 環境ではJSON形式、ローカルではテキスト形式でログを出力する。

使い方:
    from v2.logging_config import setup_logging
    setup_logging()

環境変数:
    LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL) デフォルト: INFO
    K_SERVICE / CLOUD_RUN_JOB: Cloud Run 環境判定（自動設定される）
"""

import json
import logging
import os


class CloudLoggingFormatter(logging.Formatter):
    """Cloud Logging互換のJSONフォーマッタ

    Cloud Run の stdout は Cloud Logging に転送されるが、
    JSON形式で `severity` フィールドを含めることで
    ログレベルが正しくマッピングされる。
    """

    LEVEL_TO_SEVERITY = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "severity": self.LEVEL_TO_SEVERITY.get(record.levelname, "DEFAULT"),
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> None:
    """ログ設定を初期化する

    Cloud Run 環境（K_SERVICE または CLOUD_RUN_JOB 環境変数が存在する場合）では
    Cloud Logging 互換の JSON フォーマットを使用し、ローカルではテキスト形式を使用する。
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Cloud Run 環境判定（K_SERVICE: Cloud Run Services, CLOUD_RUN_JOB: Cloud Run Jobs）
    is_cloud = bool(os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"))

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    handler = logging.StreamHandler()
    if is_cloud:
        handler.setFormatter(CloudLoggingFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
