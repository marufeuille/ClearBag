"""プロファイル CRUD の E2E テスト

Firestore Emulator を使って profiles サブコレクションの
作成・一覧・更新・削除を検証する。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

_PROFILE_TARO = {"name": "太郎", "grade": "小学1年生", "keywords": "算数"}
_PROFILE_HANAKO = {"name": "花子", "grade": "幼稚園", "keywords": ""}


class TestProfileCRUD:
    """プロファイルの CRUD 操作テスト"""

    def test_create_profile_returns_201(self, e2e_client):
        """プロファイルを作成すると 201 と生成 ID を返す"""
        r = e2e_client.post("/api/profiles", json=_PROFILE_TARO)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "太郎"
        assert data["grade"] == "小学1年生"
        assert data["keywords"] == "算数"
        assert data["id"]  # 空でない ID が返る

    def test_list_profiles_returns_all(self, e2e_client):
        """作成したプロファイルがすべて一覧に含まれる"""
        e2e_client.post("/api/profiles", json=_PROFILE_TARO)
        e2e_client.post("/api/profiles", json=_PROFILE_HANAKO)

        r = e2e_client.get("/api/profiles")
        assert r.status_code == 200
        profiles = r.json()
        assert len(profiles) == 2
        names = {p["name"] for p in profiles}
        assert names == {"太郎", "花子"}

    def test_empty_profile_list(self, e2e_client):
        """プロファイルが存在しない場合は空リストを返す"""
        # ファミリーだけ作成してプロファイルは作らない
        e2e_client.get("/api/families/me")

        r = e2e_client.get("/api/profiles")
        assert r.status_code == 200
        assert r.json() == []

    def test_update_profile(self, e2e_client):
        """プロファイルの学年を更新できる"""
        r = e2e_client.post("/api/profiles", json=_PROFILE_TARO)
        profile_id = r.json()["id"]

        r = e2e_client.put(
            f"/api/profiles/{profile_id}",
            json={"name": "太郎", "grade": "小学2年生", "keywords": "国語"},
        )
        assert r.status_code == 200
        updated = r.json()
        assert updated["grade"] == "小学2年生"
        assert updated["keywords"] == "国語"
        assert updated["id"] == profile_id

    def test_delete_profile(self, e2e_client):
        """プロファイルを削除すると一覧から消える"""
        r = e2e_client.post("/api/profiles", json=_PROFILE_TARO)
        profile_id = r.json()["id"]

        r = e2e_client.delete(f"/api/profiles/{profile_id}")
        assert r.status_code == 204

        r = e2e_client.get("/api/profiles")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_update_nonexistent_profile_returns_404(self, e2e_client):
        """存在しないプロファイルの更新は 404 を返す"""
        r = e2e_client.put(
            "/api/profiles/nonexistent-id",
            json={"name": "誰か", "grade": "不明", "keywords": ""},
        )
        assert r.status_code == 404

    def test_delete_nonexistent_profile_returns_404(self, e2e_client):
        """存在しないプロファイルの削除は 404 を返す"""
        # ファミリーを先に作成
        e2e_client.get("/api/families/me")

        r = e2e_client.delete("/api/profiles/nonexistent-id")
        assert r.status_code == 404
