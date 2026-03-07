"""分析イベントログユーティリティ

Cloud Logging sink → BigQuery パイプラインのためのビジネスイベントログ出力。
CloudLoggingFormatter の extra_fields 機構を活用して構造化フィールドを JSON に埋め込む。

使い方:
    from v2.analytics import log_event
    log_event("document_uploaded", family_id="...", uid="...", file_size=1234)
"""

import logging
import os

_logger = logging.getLogger("v2.analytics")
_PRODUCT_ID = os.environ.get("PRODUCT_ID", "clearbag")


def log_event(log_type: str, **fields) -> None:
    """構造化された分析イベントをログ出力する。

    Cloud Logging の jsonPayload に log_type フィールドが埋め込まれ、
    Log Sink フィルタ（jsonPayload.log_type:*）でキャプチャされる。

    Args:
        log_type: イベント種別（例: "document_uploaded", "access_log"）
        **fields: 追加フィールド（family_id, uid, file_size など）
    """
    _logger.info(
        log_type,
        extra={
            "extra_fields": {
                "log_type": log_type,
                "product_id": _PRODUCT_ID,
                **fields,
            }
        },
    )
