"""タスク API のユニットテスト

dependency_overrides を使ってリポジトリをモックに差し替える。
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import (
    FamilyContext,
    get_document_repo,
    get_family_context,
)

_UID = "test-user-uid"
_FAMILY_ID = "test-family-id"
_FAMILY_CONTEXT = FamilyContext(uid=_UID, family_id=_FAMILY_ID, role="owner")


@pytest.fixture
def mock_doc_repo():
    return MagicMock()


@pytest.fixture
def client(mock_doc_repo):
    """モックを差し込んだ FastAPI テストクライアント"""
    app.dependency_overrides[get_family_context] = lambda: _FAMILY_CONTEXT
    app.dependency_overrides[get_document_repo] = lambda: mock_doc_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestUpdateTask:
    """PATCH /api/tasks/{task_id} のテスト"""

    def test_update_returns_200_when_found(self, client, mock_doc_repo):
        """タスクが見つかった場合 200 と completed 状態を返す"""
        # Arrange
        mock_doc_repo.update_task_completed.return_value = True

        # Act
        response = client.patch("/api/tasks/task-1", json={"completed": True})

        # Assert
        assert response.status_code == 200
        assert response.json() == {"completed": True}
        mock_doc_repo.update_task_completed.assert_called_once_with(
            _FAMILY_ID, "task-1", True
        )

    def test_update_returns_404_when_not_found(self, client, mock_doc_repo):
        """タスクが見つからない場合 404 を返す"""
        # Arrange
        mock_doc_repo.update_task_completed.return_value = False

        # Act
        response = client.patch("/api/tasks/task-1", json={"completed": True})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"
