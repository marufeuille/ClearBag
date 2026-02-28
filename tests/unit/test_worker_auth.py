"""Worker OIDC 認証のユニットテスト

verify_worker_token Depends 関数が正しく動作することを検証する。
google.oauth2.id_token.verify_oauth2_token をモックして、
実際のトークン発行なしにテストする。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from v2.entrypoints.api.app import app


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """各テスト後に dependency_overrides をリセットする"""
    yield
    app.dependency_overrides.clear()


# ── 有効なトークンを持つクライアントのヘルパー ─────────────────────────────────

_VALID_EMAIL = "worker@example.iam.gserviceaccount.com"
_VALID_TOKEN = "valid.oidc.token"
_VALID_HEADERS = {"Authorization": f"Bearer {_VALID_TOKEN}"}


def _mock_verify(token, request, audience):  # noqa: ARG001
    """google.oauth2.id_token.verify_oauth2_token の正常系モック"""
    return {"email": _VALID_EMAIL, "sub": "12345"}


# ── テストケース ─────────────────────────────────────────────────────────────


def test_no_auth_header_returns_401():
    """Authorization ヘッダーなしのリクエストは 401 を返す"""
    with patch.dict("os.environ", {"WORKER_SERVICE_ACCOUNT_EMAIL": _VALID_EMAIL}):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/worker/analyze",
            json={
                "uid": "u1",
                "family_id": "f1",
                "document_id": "d1",
                "storage_path": "uploads/f1/d1.pdf",
                "mime_type": "application/pdf",
            },
        )
    assert response.status_code == 401


def test_invalid_token_returns_401():
    """検証に失敗するトークンは 401 を返す"""

    def _raise(token, request, audience):  # noqa: ARG001
        raise ValueError("invalid token")

    with (
        patch.dict("os.environ", {"WORKER_SERVICE_ACCOUNT_EMAIL": _VALID_EMAIL}),
        patch("v2.entrypoints.api.worker_auth.id_token.verify_oauth2_token", _raise),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/worker/analyze",
            headers={"Authorization": "Bearer bad.token"},
            json={
                "uid": "u1",
                "family_id": "f1",
                "document_id": "d1",
                "storage_path": "uploads/f1/d1.pdf",
                "mime_type": "application/pdf",
            },
        )
    assert response.status_code == 401


def test_email_mismatch_returns_401():
    """有効なトークンでも email が一致しない場合は 401 を返す"""

    def _wrong_email(token, request, audience):  # noqa: ARG001
        return {"email": "attacker@evil.iam.gserviceaccount.com"}

    with (
        patch.dict("os.environ", {"WORKER_SERVICE_ACCOUNT_EMAIL": _VALID_EMAIL}),
        patch(
            "v2.entrypoints.api.worker_auth.id_token.verify_oauth2_token", _wrong_email
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/worker/analyze",
            headers=_VALID_HEADERS,
            json={
                "uid": "u1",
                "family_id": "f1",
                "document_id": "d1",
                "storage_path": "uploads/f1/d1.pdf",
                "mime_type": "application/pdf",
            },
        )
    assert response.status_code == 401


def test_valid_token_accepted():
    """正しいサービスアカウントの OIDC トークンはリクエストを通す"""
    mock_run = MagicMock()

    with (
        patch.dict("os.environ", {"WORKER_SERVICE_ACCOUNT_EMAIL": _VALID_EMAIL}),
        patch(
            "v2.entrypoints.api.worker_auth.id_token.verify_oauth2_token", _mock_verify
        ),
        patch("v2.entrypoints.worker.run_analysis_sync", mock_run),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/worker/analyze",
            headers=_VALID_HEADERS,
            json={
                "uid": "u1",
                "family_id": "f1",
                "document_id": "d1",
                "storage_path": "uploads/f1/d1.pdf",
                "mime_type": "application/pdf",
            },
        )
    assert response.status_code == 200


def test_local_mode_skips_verification():
    """LOCAL_MODE=true のときはトークンなしでもリクエストを通す"""
    mock_run = MagicMock()

    with (
        patch.dict(
            "os.environ",
            {"LOCAL_MODE": "true", "WORKER_SERVICE_ACCOUNT_EMAIL": _VALID_EMAIL},
        ),
        patch("v2.entrypoints.worker.run_analysis_sync", mock_run),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/worker/analyze",
            # Authorization ヘッダーなし
            json={
                "uid": "u1",
                "family_id": "f1",
                "document_id": "d1",
                "storage_path": "uploads/f1/d1.pdf",
                "mime_type": "application/pdf",
            },
        )
    assert response.status_code == 200


def test_morning_digest_also_protected():
    """/worker/morning-digest も同じ認証 Depends で保護されている"""
    with patch.dict("os.environ", {"WORKER_SERVICE_ACCOUNT_EMAIL": _VALID_EMAIL}):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/worker/morning-digest")
    assert response.status_code == 401


def test_missing_env_var_returns_401():
    """WORKER_SERVICE_ACCOUNT_EMAIL 未設定時は fail-closed で 401 を返す"""
    env = {
        k: v
        for k, v in __import__("os").environ.items()
        if k != "WORKER_SERVICE_ACCOUNT_EMAIL"
    }

    with patch.dict("os.environ", env, clear=True):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/worker/analyze",
            headers=_VALID_HEADERS,
            json={
                "uid": "u1",
                "family_id": "f1",
                "document_id": "d1",
                "storage_path": "uploads/f1/d1.pdf",
                "mime_type": "application/pdf",
            },
        )
    assert response.status_code == 401
