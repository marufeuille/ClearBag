"""tests for scripts/deactivate_user.py"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from scripts.deactivate_user import deactivate_user, resolve_uid_by_email


class TestDeactivateUser:
    """deactivate_user() のテスト"""

    def _make_db(self) -> MagicMock:
        db = MagicMock()
        return db

    def test_deactivate_active_user(self):
        """有効ユーザーを停止 -> is_activated: False が書き込まれる"""
        db = self._make_db()
        user_data = {"is_activated": True, "email": "test@example.com"}

        result = deactivate_user(db, "uid-123", user_data, dry_run=False)

        assert result is True
        db.collection.assert_called_once_with("users")
        db.collection("users").document.assert_called_with("uid-123")
        db.collection("users").document("uid-123").set.assert_called_once_with(
            {"is_activated": False}, merge=True
        )

    def test_skip_already_inactive_user(self):
        """既に停止済みユーザーはスキップ"""
        db = self._make_db()
        user_data = {"is_activated": False, "email": "test@example.com"}

        result = deactivate_user(db, "uid-123", user_data, dry_run=False)

        assert result is False
        db.collection("users").document("uid-123").set.assert_not_called()

    def test_skip_not_activated_user(self):
        """is_activated フィールドがないユーザーはスキップ"""
        db = self._make_db()
        user_data = {"email": "test@example.com"}

        result = deactivate_user(db, "uid-123", user_data, dry_run=False)

        assert result is False

    def test_dry_run_does_not_write(self):
        """dry-run 時は Firestore 書き込みが呼ばれない"""
        db = self._make_db()
        user_data = {"is_activated": True}

        result = deactivate_user(db, "uid-123", user_data, dry_run=True)

        assert result is True
        db.collection("users").document("uid-123").set.assert_not_called()


class TestResolveUidByEmail:
    """resolve_uid_by_email() のテスト"""

    @patch("scripts.deactivate_user._init_firebase")
    @patch("scripts.deactivate_user.fb_auth")
    def test_resolve_uid_by_email(self, mock_auth, mock_init):
        """メールアドレス -> UID 変換"""
        mock_user = MagicMock()
        mock_user.uid = "resolved-uid-456"
        mock_auth.get_user_by_email.return_value = mock_user

        uid = resolve_uid_by_email("user@example.com")

        assert uid == "resolved-uid-456"
        mock_auth.get_user_by_email.assert_called_once_with("user@example.com")

    @patch("scripts.deactivate_user._init_firebase")
    @patch("scripts.deactivate_user.fb_auth")
    def test_resolve_uid_by_email_not_found(self, mock_auth, mock_init):
        """存在しないメールアドレスで SystemExit"""
        from firebase_admin import auth as real_auth

        mock_auth.UserNotFoundError = real_auth.UserNotFoundError
        mock_auth.get_user_by_email.side_effect = real_auth.UserNotFoundError(
            "not found"
        )

        with pytest.raises(SystemExit):
            resolve_uid_by_email("unknown@example.com")
