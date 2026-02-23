#!/usr/bin/env python3
"""CLI Entrypoint - コマンドラインから実行

使い方:
    python -m v2.entrypoints.cli

環境変数:
    LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR) デフォルト: INFO
    K_SERVICE / CLOUD_RUN_JOB: Cloud Run 環境では自動設定されJSON形式ログに切替
"""

import logging
import sys

from v2.entrypoints.factory import create_orchestrator
from v2.logging_config import setup_logging


def main():
    """メインエントリーポイント"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("School Agent v2 - Starting")

    try:
        # Orchestrator生成（DI組み立て）
        logger.info("Creating orchestrator...")
        orchestrator = create_orchestrator()

        # 実行
        logger.info("Running orchestrator...")
        results = orchestrator.run()

        # 結果ログ出力
        logger.info("Processing Complete - %d file(s) processed", len(results))

        for i, result in enumerate(results, 1):
            if result.error:
                logger.error(
                    "[%d] %s - Error: %s", i, result.file_info.name, result.error
                )
            else:
                logger.info(
                    "[%d] %s - category=%s events=%d tasks=%d notification=%s archived=%s",
                    i,
                    result.file_info.name,
                    result.analysis.category.value,
                    result.events_created,
                    result.tasks_created,
                    result.notification_sent,
                    result.archived,
                )

        # エラーがあったファイルがあれば終了コード1
        errors = [r for r in results if r.error]
        if errors:
            logger.warning("%d file(s) had errors", len(errors))
            sys.exit(1)

        logger.info("All files processed successfully")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)

    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
