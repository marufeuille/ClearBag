"""Cloud Functions デプロイ用エントリーポイント（v2版）

このファイルはGCP Cloud Functionsのデプロイ時に参照されます。

デプロイコマンド:
    gcloud functions deploy school-agent-v2 \\
        --gen2 \\
        --runtime=python313 \\
        --region=us-central1 \\
        --source=. \\
        --entry-point=school_agent_http \\
        --trigger-http \\
        --allow-unauthenticated \\
        --timeout=540s \\
        --memory=512Mi \\
        --set-env-vars PROJECT_ID=xxx,SPREADSHEET_ID=xxx,...
"""

from v2.entrypoints.cloud_function import school_agent_http

# Cloud Functionsはこのモジュールから school_agent_http をインポートする
