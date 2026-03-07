"""アカウント削除 API のユニットテスト"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from v2.domain.ports import BlobStorage, FamilyRepository, UserConfigRepository
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import (
    FamilyContext,
    get_blob_storage,
    get_family_context,
    get_family_repo,
    get_user_config_repo,
)


def _make_client(uid: str, family_id: str, role: str, members: list[dict]):
    ctx = FamilyContext(uid=uid, family_id=family_id, role=role)
    user_repo = MagicMock(spec=UserConfigRepository)
    family_repo = MagicMock(spec=FamilyRepository)
    family_repo.list_members.return_value = members
    blob = MagicMock(spec=BlobStorage)

    app.dependency_overrides[get_family_context] = lambda: ctx
    app.dependency_overrides[get_user_config_repo] = lambda: user_repo
    app.dependency_overrides[get_family_repo] = lambda: family_repo
    app.dependency_overrides[get_blob_storage] = lambda: blob

    return TestClient(app), user_repo, family_repo, blob


class TestDeleteAccount:
    def teardown_method(self):
        app.dependency_overrides.clear()

    @patch("v2.entrypoints.api.routes.account.fb_auth.delete_user")
    def test_owner_single_member_deletes_family(self, mock_fb_delete):
        """オーナー1人のみ → ファミリーごと全削除"""
        uid = "owner-uid"
        family_id = "fam-1"
        client, user_repo, family_repo, blob = _make_client(
            uid, family_id, "owner", [{"uid": uid, "role": "owner"}]
        )

        res = client.delete("/api/account")

        assert res.status_code == 204
        blob.delete_by_prefix.assert_called_once_with(f"uploads/{family_id}/")
        family_repo.delete_family_cascade.assert_called_once_with(family_id)
        user_repo.delete_user.assert_called_once_with(uid)
        mock_fb_delete.assert_called_once_with(uid)

    def test_owner_with_other_members_returns_400(self):
        """オーナーかつ他メンバーあり → 400"""
        uid = "owner-uid"
        family_id = "fam-2"
        client, _, _, _ = _make_client(
            uid,
            family_id,
            "owner",
            [{"uid": uid, "role": "owner"}, {"uid": "member-uid", "role": "member"}],
        )

        res = client.delete("/api/account")

        assert res.status_code == 400

    @patch("v2.entrypoints.api.routes.account.fb_auth.delete_user")
    def test_member_deletes_only_self(self, mock_fb_delete):
        """メンバー → 自分のレコードのみ削除"""
        uid = "member-uid"
        family_id = "fam-3"
        client, user_repo, family_repo, blob = _make_client(
            uid, family_id, "member", [{"uid": uid, "role": "member"}]
        )

        res = client.delete("/api/account")

        assert res.status_code == 204
        blob.delete_by_prefix.assert_not_called()
        family_repo.delete_family_cascade.assert_not_called()
        family_repo.remove_member.assert_called_once_with(family_id, uid)
        user_repo.delete_user.assert_called_once_with(uid)
        mock_fb_delete.assert_called_once_with(uid)
