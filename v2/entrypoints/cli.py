#!/usr/bin/env python3
"""CLI Entrypoint - コマンドラインから実行

使い方:
    python -m v2.entrypoints.cli

環境変数:
    LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR) デフォルト: INFO
"""

import logging
import sys

from v2.entrypoints.factory import create_orchestrator


# ログ設定
def setup_logging():
    """ログ設定を初期化"""
    import os

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """メインエントリーポイント"""
    setup_logging()
    logger = logging.getLogger(__name__)

    print("=" * 60)
    print("School Agent v2 - Starting")
    print("=" * 60)

    try:
        # Orchestrator生成（DI組み立て）
        logger.info("Creating orchestrator...")
        orchestrator = create_orchestrator()

        # 実行
        logger.info("Running orchestrator...")
        results = orchestrator.run()

        # 結果表示
        print("\n" + "=" * 60)
        print(f"Processing Complete - {len(results)} file(s) processed")
        print("=" * 60)

        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.file_info.name}")
            print(f"    Status: {'✅ Success' if not result.error else '❌ Error'}")

            if result.error:
                print(f"    Error: {result.error}")
                continue

            print(f"    Summary: {result.analysis.summary}")
            print(f"    Category: {result.analysis.category.value}")
            print(f"    Events Created: {result.events_created}")
            print(f"    Tasks Created: {result.tasks_created}")
            print(f"    Notification Sent: {'Yes' if result.notification_sent else 'No'}")
            print(f"    Archived: {'Yes' if result.archived else 'No'}")

        # エラーがあったファイルがあれば終了コード1
        errors = [r for r in results if r.error]
        if errors:
            logger.warning(f"{len(errors)} file(s) had errors")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("✅ All files processed successfully")
        print("=" * 60)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.exception("Fatal error")
        print(f"\n❌ Fatal Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
