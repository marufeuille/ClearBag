"""POST /api/auth/register エンドポイントのユニットテスト

dependency_overrides で get_auth_info と Firestore クライアントをモックに差し替える。
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import AuthInfo, get_auth_info

_UID = "test-uid"
_EMAIL = "test@example.com"
_AUTH_INFO = AuthInfo(uid=_UID, email=_EMAIL, display_name="Test User")

_VALID_CODE = "SPRING2026"
_FUTURE = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)
_PAST = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)


def _make_code_snap(data: dict | None, exists: bool = True) -> MagicMock:
    snap = MagicMock()
    snap.exists = exists
    snap.to_dict.return_value = data
    return snap


def _make_user_snap(is_activated: bool = False) -> MagicMock:
    snap = MagicMock()
    snap.to_dict.return_value = {"is_activated": is_activated}
    return snap


@pytest.fixture
def client():
    app.dependency_overrides[get_auth_info] = lambda: _AUTH_INFO
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestRegisterWithCode:
    def test_invalid_code_returns_404(self, client: TestClient):
        # Arrange: コードが存在しない
        code_snap = _make_code_snap(None, exists=False)
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = (
            code_snap
        )

        with patch(
            "v2.entrypoints.api.routes.auth._get_firestore_client", return_value=mock_db
        ):
            # Act
            response = client.post("/api/auth/register", json={"code": "INVALID"})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "INVALID_CODE"

    def test_expired_code_returns_400(self, client: TestClient):
        # Arrange: 期限切れコード
        code_snap = _make_code_snap(
            {"expires_at": _PAST, "used_count": 0, "max_uses": 10}
        )
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = (
            code_snap
        )

        with patch(
            "v2.entrypoints.api.routes.auth._get_firestore_client", return_value=mock_db
        ):
            response = client.post("/api/auth/register", json={"code": _VALID_CODE})

        assert response.status_code == 400
        assert response.json()["detail"] == "CODE_EXPIRED"

    def test_exhausted_code_returns_400(self, client: TestClient):
        # Arrange: 上限到達コード
        code_snap = _make_code_snap(
            {"expires_at": _FUTURE, "used_count": 5, "max_uses": 5}
        )
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = (
            code_snap
        )

        with patch(
            "v2.entrypoints.api.routes.auth._get_firestore_client", return_value=mock_db
        ):
            response = client.post("/api/auth/register", json={"code": _VALID_CODE})

        assert response.status_code == 400
        assert response.json()["detail"] == "CODE_EXHAUSTED"

    def test_already_activated_is_idempotent(self, client: TestClient):
        # Arrange: 有効コード + 既アクティベート済みユーザー
        code_snap = _make_code_snap(
            {"expires_at": _FUTURE, "used_count": 1, "max_uses": 10}
        )
        user_snap = _make_user_snap(is_activated=True)

        mock_db = MagicMock()
        # collection("service_codes").document(code).get() → code_snap
        # collection("users").document(uid).get() → user_snap
        mock_coll = MagicMock()
        mock_db.collection.return_value = mock_coll
        mock_coll.document.return_value.get.side_effect = [code_snap, user_snap]

        with patch(
            "v2.entrypoints.api.routes.auth._get_firestore_client", return_value=mock_db
        ):
            response = client.post("/api/auth/register", json={"code": _VALID_CODE})

        assert response.status_code == 200
        assert response.json()["activated"] is True
        assert response.json()["already_activated"] is True
        assert "登録済み" in response.json()["message"]

    def test_successful_activation(self, client: TestClient):
        # Arrange: 有効コード + 未アクティベートユーザー
        code_snap = _make_code_snap(
            {"expires_at": _FUTURE, "used_count": 0, "max_uses": 10}
        )
        user_snap = _make_user_snap(is_activated=False)

        mock_db = MagicMock()
        mock_coll = MagicMock()
        mock_db.collection.return_value = mock_coll
        # トランザクション内でも code_ref.get() が呼ばれるため 3 エントリ
        mock_coll.document.return_value.get.side_effect = [
            code_snap,
            user_snap,
            code_snap,
        ]
        mock_db.transaction.return_value = MagicMock()

        with (
            patch(
                "v2.entrypoints.api.routes.auth._get_firestore_client",
                return_value=mock_db,
            ),
            patch(
                "v2.entrypoints.api.routes.auth.firestore.transactional", lambda fn: fn
            ),
            patch(
                "v2.entrypoints.api.routes.auth.fb_auth.set_custom_user_claims"
            ) as mock_claims,
        ):
            response = client.post("/api/auth/register", json={"code": _VALID_CODE})

        assert response.status_code == 200
        assert response.json()["activated"] is True
        assert response.json()["already_activated"] is False
        # Custom Claims が正しいパラメータで呼ばれること（Cold Start 回避のため必須）
        mock_claims.assert_called_once_with(_UID, {"is_activated": True})

    def test_successful_activation_claims_failure_is_nonfatal(self, client: TestClient):
        # Arrange: Custom Claims 設定が失敗しても 200 を返すこと
        code_snap = _make_code_snap(
            {"expires_at": _FUTURE, "used_count": 0, "max_uses": 10}
        )
        user_snap = _make_user_snap(is_activated=False)

        mock_db = MagicMock()
        mock_coll = MagicMock()
        mock_db.collection.return_value = mock_coll
        mock_coll.document.return_value.get.side_effect = [
            code_snap,
            user_snap,
            code_snap,
        ]
        mock_db.transaction.return_value = MagicMock()

        with (
            patch(
                "v2.entrypoints.api.routes.auth._get_firestore_client",
                return_value=mock_db,
            ),
            patch(
                "v2.entrypoints.api.routes.auth.firestore.transactional", lambda fn: fn
            ),
            patch(
                "v2.entrypoints.api.routes.auth.fb_auth.set_custom_user_claims",
                side_effect=Exception("Firebase Auth unavailable"),
            ),
        ):
            response = client.post("/api/auth/register", json={"code": _VALID_CODE})

        # Custom Claims 失敗は non-fatal — Firestore への is_activated 設定は完了済み
        assert response.status_code == 200
        assert response.json()["activated"] is True

    def test_unlimited_code_succeeds(self, client: TestClient):
        # Arrange: max_uses=None（無制限コード）
        code_snap = _make_code_snap(
            {"expires_at": _FUTURE, "used_count": 9999, "max_uses": None}
        )
        user_snap = _make_user_snap(is_activated=False)

        mock_db = MagicMock()
        mock_coll = MagicMock()
        mock_db.collection.return_value = mock_coll
        # トランザクション内でも code_ref.get() が呼ばれるため 3 エントリ
        mock_coll.document.return_value.get.side_effect = [
            code_snap,
            user_snap,
            code_snap,
        ]
        mock_db.transaction.return_value = MagicMock()

        with (
            patch(
                "v2.entrypoints.api.routes.auth._get_firestore_client",
                return_value=mock_db,
            ),
            patch(
                "v2.entrypoints.api.routes.auth.firestore.transactional", lambda fn: fn
            ),
            patch("v2.entrypoints.api.routes.auth.fb_auth.set_custom_user_claims"),
        ):
            response = client.post("/api/auth/register", json={"code": _VALID_CODE})

        assert response.status_code == 200
        assert response.json()["activated"] is True
