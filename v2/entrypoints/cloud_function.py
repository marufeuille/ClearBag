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
    - SLACK_BOT_TOKEN (optional)
    - SLACK_CHANNEL_ID (optional)
"""

import logging
import functions_framework
from v2.entrypoints.factory import create_orchestrator

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
    logger.info("School Agent v2 triggered via HTTP")

    try:
        # Orchestrator生成・実行
        orchestrator = create_orchestrator()
        results = orchestrator.run()

        # 結果サマリー
        success_count = len([r for r in results if not r.error])
        error_count = len([r for r in results if r.error])

        response_message = f"Processed {len(results)} file(s): {success_count} success, {error_count} errors"
        logger.info(response_message)

        # エラーがあっても200を返す（部分的成功を許容）
        # 完全失敗のみ500を返したい場合は条件を変更
        return response_message, 200

    except Exception as e:
        logger.exception("Fatal error in Cloud Function")
        return f"Error: {str(e)}", 500
