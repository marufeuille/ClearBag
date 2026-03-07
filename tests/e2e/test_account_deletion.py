"""アカウント削除 E2E テスト（Firestore Emulator 使用）"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from v2.adapters.cloud_storage import GCSBlobStorage
from v2.adapters.firestore_repository import (
    FirestoreFamilyRepository,
    FirestoreUserConfigRepository,
)
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import (
    FamilyContext,
    _get_firestore_client,
    get_blob_storage,
    get_family_context,
    get_family_repo,
    get_user_config_repo,
)

pytestmark = pytest.mark.e2e


@pytest.fixture
def db():
    return _get_firestore_client()


@pytest.fixture
def family_repo(db):
    return FirestoreFamilyRepository(db)


@pytest.fixture
def user_repo(db):
    return FirestoreUserConfigRepository(db)


@pytest.fixture
def blob_storage():
    return MagicMock(spec=GCSBlobStorage)


def _setup_client(
    uid: str, family_id: str, role: str, user_repo, family_repo, blob_storage
):
    ctx = FamilyContext(uid=uid, family_id=family_id, role=role)
    app.dependency_overrides[get_family_context] = lambda: ctx
    app.dependency_overrides[get_user_config_repo] = lambda: user_repo
    app.dependency_overrides[get_family_repo] = lambda: family_repo
    app.dependency_overrides[get_blob_storage] = lambda: blob_storage
    return TestClient(app)


class TestAccountDeletionE2E:
    def teardown_method(self):
        app.dependency_overrides.clear()

    @patch("v2.entrypoints.api.routes.account.fb_auth.delete_user")
    def test_owner_deletion_removes_all_firestore_data(
        self, mock_fb, db, family_repo, user_repo, blob_storage
    ):
        """オーナー削除後、Firestore のファミリーデータが消えること"""
        uid = "e2e-owner-uid"
        family_id = "e2e-fam-1"

        # セットアップ: ファミリー・メンバー・ユーザー作成
        family_repo.create_family(family_id, uid, "テストファミリー")
        family_repo.add_member(family_id, uid, "owner", "オーナー", "owner@example.com")
        user_repo.update_user(uid, {"family_id": family_id, "is_activated": True})

        client = _setup_client(
            uid, family_id, "owner", user_repo, family_repo, blob_storage
        )

        res = client.delete("/api/account")
        assert res.status_code == 204

        # 検証: ファミリードキュメントが削除されていること
        fam_snap = db.collection("families").document(family_id).get()
        assert not fam_snap.exists

        # 検証: users/{uid} が削除されていること
        user_snap = db.collection("users").document(uid).get()
        assert not user_snap.exists

        # 検証: GCS 削除が呼ばれていること
        blob_storage.delete_by_prefix.assert_called_once_with(f"uploads/{family_id}/")

    @patch("v2.entrypoints.api.routes.account.fb_auth.delete_user")
    def test_member_deletion_leaves_family(
        self, mock_fb, db, family_repo, user_repo, blob_storage
    ):
        """メンバー削除後、ファミリーは残りメンバーレコードのみ消えること"""
        owner_uid = "e2e-owner-2"
        member_uid = "e2e-member-2"
        family_id = "e2e-fam-2"

        family_repo.create_family(family_id, owner_uid, "テストファミリー2")
        family_repo.add_member(
            family_id, owner_uid, "owner", "オーナー", "owner2@example.com"
        )
        family_repo.add_member(
            family_id, member_uid, "member", "メンバー", "member2@example.com"
        )
        user_repo.update_user(
            member_uid, {"family_id": family_id, "is_activated": True}
        )

        client = _setup_client(
            member_uid, family_id, "member", user_repo, family_repo, blob_storage
        )

        res = client.delete("/api/account")
        assert res.status_code == 204

        # ファミリーは残っている
        fam_snap = db.collection("families").document(family_id).get()
        assert fam_snap.exists

        # メンバーレコードが消えている
        member_snap = (
            db.collection("families")
            .document(family_id)
            .collection("members")
            .document(member_uid)
            .get()
        )
        assert not member_snap.exists

        # users/{member_uid} が消えている
        user_snap = db.collection("users").document(member_uid).get()
        assert not user_snap.exists
