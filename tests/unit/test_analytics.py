"""analytics.py のユニットテスト

log_event() の構造化ログ出力と、
アクセスログミドルウェア・JWT デコードヘルパーの動作を検証する。
"""

import base64
import json
import logging
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from v2.analytics import log_event
from v2.entrypoints.api.app import _extract_uid_from_bearer, app
from v2.entrypoints.api.deps import FamilyContext, get_document_repo, get_family_context

# ─── log_event() テスト ─────────────────────────────────────────────────────


class TestLogEvent:
    """log_event() が正しい extra_fields 構造でログ出力すること"""

    def test_log_event_emits_info_log(self, caplog):
        """log_event() が INFO レベルでログを出力する"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            log_event("document_uploaded", family_id="f1", uid="u1", file_size=1234)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"

    def test_log_event_message_is_log_type(self, caplog):
        """ログのメッセージが log_type と一致する"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            log_event("access_log", path="/api/documents")

        assert caplog.records[0].getMessage() == "access_log"

    def test_log_event_extra_fields_contains_log_type(self, caplog):
        """extra_fields に log_type が含まれる"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            log_event("document_uploaded", family_id="fam1")

        record = caplog.records[0]
        assert hasattr(record, "extra_fields")
        assert record.extra_fields["log_type"] == "document_uploaded"

    def test_log_event_extra_fields_contains_product_id(self, caplog):
        """extra_fields に product_id が含まれる"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            log_event("access_log")

        record = caplog.records[0]
        assert "product_id" in record.extra_fields

    def test_log_event_extra_fields_contains_custom_fields(self, caplog):
        """追加フィールドが extra_fields に含まれる"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            log_event("document_uploaded", family_id="fam1", uid="u1", file_size=5000)

        record = caplog.records[0]
        assert record.extra_fields["family_id"] == "fam1"
        assert record.extra_fields["uid"] == "u1"
        assert record.extra_fields["file_size"] == 5000

    def test_log_event_none_values_are_included(self, caplog):
        """None 値のフィールドも extra_fields に含まれる"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            log_event("document_uploaded", num_pages=None)

        record = caplog.records[0]
        assert record.extra_fields["num_pages"] is None


# ─── _extract_uid_from_bearer() テスト ──────────────────────────────────────


def _make_jwt_with_payload(payload: dict) -> str:
    """テスト用 JWT を生成する（署名部はダミー）"""
    header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.fake-signature"


class TestExtractUidFromBearer:
    """_extract_uid_from_bearer() の動作テスト"""

    def _make_request(self, auth_header: str | None):
        """Authorization ヘッダーを持つダミーリクエストを生成する"""
        from starlette.requests import Request

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
        if auth_header is not None:
            scope["headers"] = [(b"authorization", auth_header.encode())]
        return Request(scope)

    def test_extracts_uid_from_user_id_claim(self):
        """Firebase JWT の user_id クレームから UID を取得する"""
        token = _make_jwt_with_payload({"user_id": "firebase-uid-123"})
        request = self._make_request(f"Bearer {token}")
        assert _extract_uid_from_bearer(request) == "firebase-uid-123"

    def test_extracts_uid_from_sub_claim(self):
        """標準 JWT の sub クレームから UID を取得する"""
        token = _make_jwt_with_payload({"sub": "sub-uid-456"})
        request = self._make_request(f"Bearer {token}")
        assert _extract_uid_from_bearer(request) == "sub-uid-456"

    def test_returns_none_when_no_auth_header(self):
        """Authorization ヘッダーなしの場合 None を返す"""
        request = self._make_request(None)
        assert _extract_uid_from_bearer(request) is None

    def test_returns_none_when_not_bearer(self):
        """Bearer 形式でない場合 None を返す"""
        request = self._make_request("Basic dXNlcjpwYXNz")
        assert _extract_uid_from_bearer(request) is None

    def test_returns_none_for_malformed_token(self):
        """不正な形式の JWT は None を返す"""
        request = self._make_request("Bearer not.a.valid.jwt.token.here")
        assert _extract_uid_from_bearer(request) is None


# ─── アクセスログミドルウェア テスト ───────────────────────────────────────────


_FAMILY_CONTEXT = FamilyContext(uid="test-uid", family_id="test-family", role="owner")


@pytest.fixture
def client_with_override():
    """FamilyContext と DocumentRepo をオーバーライドしたテストクライアント。

    Firestore への実接続を防ぐため、doc_repo もモックに差し替える。
    """
    mock_repo = MagicMock()
    mock_repo.list.return_value = []
    app.dependency_overrides[get_family_context] = lambda: _FAMILY_CONTEXT
    app.dependency_overrides[get_document_repo] = lambda: mock_repo
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


class TestAccessLogMiddleware:
    """アクセスログミドルウェアの動作テスト"""

    def test_health_endpoint_not_logged(self, client_with_override, caplog):
        """/health エンドポイントはログを出力しない"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            client_with_override.get("/health")

        log_types = [
            r.extra_fields.get("log_type")
            for r in caplog.records
            if hasattr(r, "extra_fields")
        ]
        assert "access_log" not in log_types

    def test_api_endpoint_logged(self, client_with_override, caplog):
        """/api/* エンドポイントはアクセスログを出力する"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            client_with_override.get("/api/documents")

        access_logs = [
            r.extra_fields
            for r in caplog.records
            if hasattr(r, "extra_fields")
            and r.extra_fields.get("log_type") == "access_log"
        ]
        assert len(access_logs) >= 1
        log = access_logs[0]
        assert log["method"] == "GET"
        assert log["path"] == "/api/documents"
        assert "status_code" in log
        assert "response_time_ms" in log

    def test_access_log_without_auth_has_null_uid(self, client_with_override, caplog):
        """認証ヘッダーなしのリクエストは uid=None でログ出力される"""
        with caplog.at_level(logging.INFO, logger="v2.analytics"):
            client_with_override.get("/api/documents")

        access_logs = [
            r.extra_fields
            for r in caplog.records
            if hasattr(r, "extra_fields")
            and r.extra_fields.get("log_type") == "access_log"
        ]
        assert len(access_logs) >= 1
        assert access_logs[0]["uid"] is None
