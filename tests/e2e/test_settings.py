"""設定 API の E2E テスト

GET /api/settings でデフォルト値の確認、
PATCH /api/settings で通知設定の更新を検証する。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


class TestSettings:
    """GET /api/settings, PATCH /api/settings のテスト"""

    def test_get_settings_returns_defaults(self, e2e_client):
        """初回アクセスでデフォルト設定を返す"""
        r = e2e_client.get("/api/settings")
        assert r.status_code == 200
        data = r.json()
        assert data["plan"] == "free"
        assert data["documents_this_month"] == 0
        assert "ical_url" in data
        assert data["ical_url"]  # 空でない URL が返る
        assert data["notification_email"] is True  # デフォルト on
        assert data["notification_web_push"] is False  # デフォルト off

    def test_update_notification_email(self, e2e_client):
        """メール通知を無効化できる"""
        r = e2e_client.patch("/api/settings", json={"notification_email": False})
        assert r.status_code == 200
        data = r.json()
        assert data["notification_email"] is False
        assert data["notification_web_push"] is False  # 変更なし

    def test_update_notification_web_push(self, e2e_client):
        """Web Push 通知を有効化できる"""
        r = e2e_client.patch("/api/settings", json={"notification_web_push": True})
        assert r.status_code == 200
        data = r.json()
        assert data["notification_email"] is True  # 変更なし
        assert data["notification_web_push"] is True

    def test_update_both_notifications(self, e2e_client):
        """両方の通知設定を同時に更新できる"""
        r = e2e_client.patch(
            "/api/settings",
            json={"notification_email": False, "notification_web_push": True},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["notification_email"] is False
        assert data["notification_web_push"] is True

    def test_ical_url_is_stable_across_requests(self, e2e_client):
        """同一ユーザーの ical_url は複数回リクエストしても同じ値になる"""
        r1 = e2e_client.get("/api/settings")
        r2 = e2e_client.get("/api/settings")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["ical_url"] == r2.json()["ical_url"]

    def test_patch_with_no_fields_is_noop(self, e2e_client):
        """空のリクエストボディは設定を変更しない"""
        r_before = e2e_client.get("/api/settings")
        r = e2e_client.patch("/api/settings", json={})
        assert r.status_code == 200
        assert r.json()["notification_email"] == r_before.json()["notification_email"]
