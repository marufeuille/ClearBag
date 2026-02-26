"""FastAPI ドキュメント API のユニットテスト

dependency_overrides を使ってリポジトリ・ストレージをモックに差し替える。
実際の Firestore / GCS は使わない。
"""

import hashlib
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from v2.domain.models import DocumentRecord
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import (
    FamilyContext,
    get_blob_storage,
    get_document_repo,
    get_family_context,
    get_family_repo,
    get_task_queue,
)

_UID = "test-user-uid"
_FAMILY_ID = "test-family-id"
_DOC_ID = "test-doc-id"
_CONTENT = b"fake-pdf-content"
_HASH = hashlib.sha256(_CONTENT).hexdigest()

_FAMILY_CONTEXT = FamilyContext(uid=_UID, family_id=_FAMILY_ID, role="owner")


@pytest.fixture
def mock_doc_repo():
    repo = MagicMock()
    repo.find_by_content_hash.return_value = None  # 重複なし
    repo.create.return_value = _DOC_ID
    repo.list.return_value = []
    repo.get.return_value = DocumentRecord(
        id=_DOC_ID,
        uid=_UID,
        status="completed",
        content_hash=_HASH,
        storage_path=f"uploads/{_FAMILY_ID}/{_DOC_ID}.pdf",
        original_filename="test.pdf",
        mime_type="application/pdf",
        summary="テスト文書",
        category="EVENT",
    )
    return repo


@pytest.fixture
def mock_family_repo():
    repo = MagicMock()
    repo.get_family.return_value = {"plan": "free", "documents_this_month": 0}
    return repo


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.upload.return_value = f"uploads/{_FAMILY_ID}/{_DOC_ID}.pdf"
    return storage


@pytest.fixture
def mock_queue():
    return MagicMock()


@pytest.fixture
def client(mock_doc_repo, mock_family_repo, mock_storage, mock_queue):
    """モックを差し込んだ FastAPI テストクライアント"""
    app.dependency_overrides[get_family_context] = lambda: _FAMILY_CONTEXT
    app.dependency_overrides[get_document_repo] = lambda: mock_doc_repo
    app.dependency_overrides[get_family_repo] = lambda: mock_family_repo
    app.dependency_overrides[get_blob_storage] = lambda: mock_storage
    app.dependency_overrides[get_task_queue] = lambda: mock_queue

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestUploadDocument:
    """POST /api/documents/upload のテスト"""

    def test_upload_returns_202(self, client):
        """正常アップロードで 202 Accepted を返す"""
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", _CONTENT, "application/pdf")},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert "id" in data

    def test_upload_idempotent_returns_existing(self, client, mock_doc_repo):
        """重複アップロード（同じハッシュ）は既存レコードを返す"""
        existing = DocumentRecord(
            id="existing-doc-id",
            uid=_UID,
            status="completed",
            content_hash=_HASH,
            storage_path=f"uploads/{_FAMILY_ID}/existing.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
        )
        mock_doc_repo.find_by_content_hash.return_value = existing

        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", _CONTENT, "application/pdf")},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["id"] == "existing-doc-id"
        # GCS アップロードや Cloud Tasks エンキューは呼ばれない
        mock_doc_repo.create.assert_not_called()

    def test_upload_rate_limit_free_plan(self, client, mock_family_repo):
        """無料プランの月 5 枚制限を超えると 402 を返す"""
        mock_family_repo.get_family.return_value = {
            "plan": "free",
            "documents_this_month": 5,
        }
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", _CONTENT, "application/pdf")},
        )
        assert response.status_code == 402

    def test_upload_premium_no_limit(self, client, mock_family_repo):
        """プレミアムプランは枚数制限なし"""
        mock_family_repo.get_family.return_value = {
            "plan": "premium",
            "documents_this_month": 100,
        }
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", _CONTENT, "application/pdf")},
        )
        assert response.status_code == 202


class TestListDocuments:
    """GET /api/documents のテスト"""

    def test_list_returns_empty(self, client):
        """ドキュメントなしの場合は空リストを返す"""
        response = client.get("/api/documents")
        assert response.status_code == 200
        assert response.json() == []


class TestGetDocument:
    """GET /api/documents/{id} のテスト"""

    def test_get_existing_document(self, client):
        """存在するドキュメントを返す"""
        response = client.get(f"/api/documents/{_DOC_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == _DOC_ID
        assert data["status"] == "completed"

    def test_get_nonexistent_returns_404(self, client, mock_doc_repo):
        """存在しないドキュメントは 404 を返す"""
        mock_doc_repo.get.return_value = None
        response = client.get("/api/documents/nonexistent-id")
        assert response.status_code == 404


class TestDeleteDocument:
    """DELETE /api/documents/{id} のテスト"""

    def test_delete_returns_204(self, client):
        """正常削除で 204 No Content を返す"""
        response = client.delete(f"/api/documents/{_DOC_ID}")
        assert response.status_code == 204

    def test_delete_nonexistent_returns_404(self, client, mock_doc_repo):
        """存在しないドキュメントの削除は 404 を返す"""
        mock_doc_repo.get.return_value = None
        response = client.delete("/api/documents/nonexistent")
        assert response.status_code == 404
