"""グローバル例外ハンドラーのユニットテスト

未処理例外が 500 JSON レスポンスになること、かつ CORS ヘッダーが付与されることを検証する。
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

_UID = "test-uid"
_FAMILY_ID = "test-family-id"
_FAMILY_CONTEXT = FamilyContext(uid=_UID, family_id=_FAMILY_ID, role="owner")
_ORIGIN = "http://localhost:3000"


@pytest.fixture
def client_with_broken_repo():
    """list_tasks が RuntimeError を投げるリポジトリを差し込んだクライアント"""
    broken_repo = MagicMock()
    broken_repo.list_tasks.side_effect = RuntimeError("Firestore index not ready")

    app.dependency_overrides[get_family_context] = lambda: _FAMILY_CONTEXT
    app.dependency_overrides[get_document_repo] = lambda: broken_repo

    # raise_server_exceptions=False で 500 をレスポンスとして受け取る
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def normal_client():
    """正常なモックを差し込んだクライアント（既存挙動の回帰確認用）"""
    normal_repo = MagicMock()
    normal_repo.list_tasks.return_value = []

    app.dependency_overrides[get_family_context] = lambda: _FAMILY_CONTEXT
    app.dependency_overrides[get_document_repo] = lambda: normal_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestUnhandledExceptionHandler:
    """グローバル例外ハンドラーのテスト"""

    def test_500_returns_json(self, client_with_broken_repo):
        """未処理例外が 500 JSON レスポンスになること"""
        response = client_with_broken_repo.get(
            "/api/tasks",
            headers={"Origin": _ORIGIN},
        )
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}

    def test_500_has_cors_header(self, client_with_broken_repo):
        """500 レスポンスに CORS ヘッダーが付与されること"""
        response = client_with_broken_repo.get(
            "/api/tasks",
            headers={"Origin": _ORIGIN},
        )
        assert response.status_code == 500
        assert "access-control-allow-origin" in response.headers

    def test_normal_request_unaffected(self, normal_client):
        """正常系リクエストが 200 を返し、既存挙動に影響がないこと"""
        response = normal_client.get(
            "/api/tasks",
            headers={"Origin": _ORIGIN},
        )
        assert response.status_code == 200
        assert response.json() == []
