"""Cloud Functions Entrypoint - GCP Cloud Functionsから実行

デプロイ例:
    gcloud functions deploy school-agent-v2 \\
        --gen2 \\
        --runtime=python313 \\
        --region=us-central1 \\
        --source=. \\
        --entry-point=school_agent_http \\
        --trigger-http \\
        --allow-unauthenticated \\
        --timeout=540s \\
        --memory=512Mi

環境変数設定:
    gcloud functions deploy時に --set-env-vars で設定するか、
    Google Cloud Consoleから設定:
    - PROJECT_ID
    - SPREADSHEET_ID
    - INBOX_FOLDER_ID
    - ARCHIVE_FOLDER_ID
    - TODOIST_API_TOKEN (optional)
    - SLACK_BOT_TOKEN (optional)
    - SLACK_CHANNEL_ID (optional)
"""

import logging
import os
from datetime import datetime
import functions_framework
from v2.entrypoints.factory import create_orchestrator

# ログレベルを環境変数から設定(デフォルト: INFO)
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

@functions_framework.http
def school_agent_http(request):
    """
    HTTP Cloud Function エントリーポイント。

    Args:
        request (flask.Request): HTTPリクエスト

    Returns:
        tuple: (レスポンステキスト, ステータスコード)
    """
    invocation_time = datetime.now()
    logger.info("=" * 80)
    logger.info("🌐 School Agent v2 triggered via HTTP")
    logger.info("🕐 Invocation time: %s", invocation_time.isoformat())
    logger.info("📊 Log level: %s", log_level)
    logger.info("=" * 80)

    try:
        # Orchestrator生成・実行
        logger.info("🏗️ Creating orchestrator...")
        orchestrator = create_orchestrator()

        logger.info("▶️ Running orchestrator...")
        run_start = datetime.now()
        results = orchestrator.run()
        run_duration = (datetime.now() - run_start).total_seconds()

        # 結果サマリー
        success_count = len([r for r in results if not r.error])
        error_count = len([r for r in results if r.error])

        response_message = f"Processed {len(results)} file(s): {success_count} success, {error_count} errors (took {run_duration:.2f}s)"
        logger.info("=" * 80)
        logger.info("✅ Cloud Function completed successfully")
        logger.info("📊 %s", response_message)
        logger.info("⏱️ Total execution time: %.2f seconds", run_duration)
        logger.info("=" * 80)

        # エラーがあっても200を返す（部分的成功を許容）
        # 完全失敗のみ500を返したい場合は条件を変更
        return response_message, 200

    except Exception as e:
        error_duration = (datetime.now() - invocation_time).total_seconds()
        logger.exception("❌ Fatal error in Cloud Function after %.2f seconds", error_duration)
        return f"Error: {str(e)}", 500
