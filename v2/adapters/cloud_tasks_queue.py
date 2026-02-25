"""Cloud Tasks Queue Adapter

TaskQueue ABC の Google Cloud Tasks 実装。
ドキュメント解析ジョブを非同期キューに追加する。

キューに入れるペイロード例:
  {
    "uid": "firebase-uid",
    "document_id": "doc-uuid",
    "storage_path": "uploads/uid/doc-uuid.pdf",
    "mime_type": "application/pdf"
  }
"""

from __future__ import annotations

import json
import logging
from base64 import b64encode

from google.cloud import tasks_v2

from v2.domain.ports import TaskQueue

logger = logging.getLogger(__name__)


class CloudTasksQueue(TaskQueue):
    """
    Google Cloud Tasks を使った TaskQueue 実装。

    タスクは HTTP ターゲットとしてワーカー URL に POST される。
    Firebase Auth の OIDC トークンでワーカーエンドポイントを保護する。
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        queue_name: str,
        worker_url: str,
        service_account_email: str,
        client: tasks_v2.CloudTasksClient | None = None,
    ) -> None:
        """
        Args:
            project_id: GCP プロジェクト ID
            location: Cloud Tasks のリージョン（例: "asia-northeast1"）
            queue_name: キュー名（例: "document-analysis"）
            worker_url: ワーカーエンドポイント URL
            service_account_email: OIDC トークン発行に使う SA メール
            client: 初期化済みクライアント（省略時は ADC で自動初期化）
        """
        self._client = client or tasks_v2.CloudTasksClient()
        self._queue_path = self._client.queue_path(project_id, location, queue_name)
        self._worker_url = worker_url
        self._service_account_email = service_account_email

    def enqueue(self, payload: dict) -> str:
        """
        ジョブを Cloud Tasks キューに追加。

        Args:
            payload: ワーカーに渡す JSON ペイロード

        Returns:
            Cloud Tasks タスク名（完全修飾リソース名）
        """
        body = json.dumps(payload).encode("utf-8")

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": self._worker_url,
                "headers": {"Content-Type": "application/json"},
                "body": b64encode(body).decode("utf-8"),
                "oidc_token": {
                    "service_account_email": self._service_account_email,
                    "audience": self._worker_url,
                },
            }
        }

        response = self._client.create_task(
            request={"parent": self._queue_path, "task": task}
        )

        logger.info(
            "Enqueued task: queue=%s, task=%s, payload_keys=%s",
            self._queue_path,
            response.name,
            list(payload.keys()),
        )
        return response.name
