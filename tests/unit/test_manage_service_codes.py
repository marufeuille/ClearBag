"""manage_service_codes.py のユニットテスト"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest
from scripts.manage_service_codes import (
    _compute_status,
    list_codes,
    revoke_code,
)

_NOW = datetime.datetime(2026, 3, 8, 12, 0, 0, tzinfo=datetime.UTC)


class TestComputeStatus:
    def test_active(self):
        data = {
            "expires_at": _NOW + datetime.timedelta(days=1),
            "max_uses": 10,
            "used_count": 3,
        }
        assert _compute_status(data, _NOW) == "active"

    def test_expired(self):
        data = {
            "expires_at": _NOW - datetime.timedelta(seconds=1),
            "max_uses": 10,
            "used_count": 3,
        }
        assert _compute_status(data, _NOW) == "expired"

    def test_exhausted(self):
        data = {
            "expires_at": _NOW + datetime.timedelta(days=1),
            "max_uses": 5,
            "used_count": 5,
        }
        assert _compute_status(data, _NOW) == "exhausted"

    def test_unlimited_uses(self):
        data = {
            "expires_at": _NOW + datetime.timedelta(days=1),
            "max_uses": None,
            "used_count": 100,
        }
        assert _compute_status(data, _NOW) == "active"


class TestListCodes:
    def test_list_codes_empty(self, capsys):
        db = MagicMock()
        db.collection.return_value.stream.return_value = []

        list_codes(db)

        captured = capsys.readouterr()
        assert "No service codes found." in captured.out

    def test_list_codes_shows_status(self, capsys):
        now = datetime.datetime.now(datetime.UTC)

        active_doc = MagicMock()
        active_doc.id = "ACTIVE01"
        active_doc.to_dict.return_value = {
            "description": "active code",
            "used_count": 2,
            "max_uses": 10,
            "expires_at": now + datetime.timedelta(days=7),
        }

        expired_doc = MagicMock()
        expired_doc.id = "EXPIRE01"
        expired_doc.to_dict.return_value = {
            "description": "expired code",
            "used_count": 0,
            "max_uses": 5,
            "expires_at": now - datetime.timedelta(days=1),
        }

        exhausted_doc = MagicMock()
        exhausted_doc.id = "EXHAUS01"
        exhausted_doc.to_dict.return_value = {
            "description": "exhausted code",
            "used_count": 10,
            "max_uses": 10,
            "expires_at": now + datetime.timedelta(days=7),
        }

        db = MagicMock()
        db.collection.return_value.stream.return_value = [
            active_doc,
            expired_doc,
            exhausted_doc,
        ]

        list_codes(db)

        captured = capsys.readouterr()
        assert "active" in captured.out
        assert "expired" in captured.out
        assert "exhausted" in captured.out
        assert "ACTIVE01" in captured.out
        assert "EXPIRE01" in captured.out
        assert "EXHAUS01" in captured.out


class TestRevokeCode:
    def test_revoke_existing_code(self):
        db = MagicMock()
        doc_ref = MagicMock()
        snap = MagicMock()
        snap.exists = True
        doc_ref.get.return_value = snap
        db.collection.return_value.document.return_value = doc_ref

        revoke_code(db, "TESTCODE", dry_run=False)

        doc_ref.update.assert_called_once()
        call_args = doc_ref.update.call_args[0][0]
        assert "expires_at" in call_args
        assert call_args["expires_at"] < datetime.datetime.now(datetime.UTC)

    def test_revoke_nonexistent_code_raises(self):
        db = MagicMock()
        doc_ref = MagicMock()
        snap = MagicMock()
        snap.exists = False
        doc_ref.get.return_value = snap
        db.collection.return_value.document.return_value = doc_ref

        with pytest.raises(SystemExit, match="not found"):
            revoke_code(db, "NOEXIST", dry_run=False)

    def test_revoke_dry_run_does_not_write(self):
        db = MagicMock()
        doc_ref = MagicMock()
        snap = MagicMock()
        snap.exists = True
        doc_ref.get.return_value = snap
        db.collection.return_value.document.return_value = doc_ref

        revoke_code(db, "TESTCODE", dry_run=True)

        doc_ref.update.assert_not_called()
