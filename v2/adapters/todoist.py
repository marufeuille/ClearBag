"""Todoist Task Service Adapter

TaskService ABCの実装。
既存 src/todoist_client.py を移植し、ABCに準拠。
"""

import logging

from todoist_api_python.api import TodoistAPI

from v2.domain.models import TaskData
from v2.domain.ports import TaskService

logger = logging.getLogger(__name__)


class TodoistAdapter(TaskService):
    """
    Todoist APIを使ったタスク管理実装。

    既存の問題点を修正:
    - 環境変数への直接依存を排除（コンストラクタで注入）
    - print → logging
    - エラーハンドリング改善
    """

    def __init__(self, api_token: str, project_id: str | None = None):
        """
        Args:
            api_token: Todoist API Token
            project_id: デフォルトのプロジェクトID（Noneの場合はInbox）
        """
        if not api_token:
            raise ValueError("api_token is required")

        self._api = TodoistAPI(api_token)
        self._project_id = project_id

    def create_task(self, task: TaskData, file_link: str = "") -> str:
        """
        Todoistにタスクを作成。

        Args:
            task: タスクデータ
            file_link: 元ファイルへのリンク

        Returns:
            str: 作成されたタスクのID

        Raises:
            Exception: タスク作成に失敗した場合
        """
        # Descriptionを組み立て
        description_parts = [
            f"Assignee: {task.assignee}",
            task.note,
        ]
        if file_link:
            description_parts.append(f"\n[Original File]({file_link})")

        description = "\n".join(description_parts)

        try:
            # Todoist APIを呼び出し
            created_task = self._api.add_task(
                content=task.title,
                description=description,
                due_string=task.due_date,  # YYYY-MM-DD形式
                project_id=self._project_id,
            )

            logger.info(
                "Created Todoist task: %s (ID: %s)",
                created_task.content,
                created_task.id,
            )
            return created_task.id

        except Exception:
            logger.exception("Failed to create Todoist task: %s", task.title)
            raise  # 呼び出し元でエラーハンドリング
