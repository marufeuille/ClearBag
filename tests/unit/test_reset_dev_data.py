"""scripts/reset_dev_data.py のユニットテスト"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestGuardProjectId:
    def test_guard_accepts_dev(self) -> None:
        """PROJECT_ID=clearbag-dev で正常通過すること。"""
        from scripts.reset_dev_data import _guard_project_id

        result = _guard_project_id("clearbag-dev")

        assert result == "clearbag-dev"

    def test_guard_rejects_prod(self) -> None:
        """PROJECT_ID=clearbag-prod で SystemExit になること。"""
        from scripts.reset_dev_data import _guard_project_id

        with pytest.raises(SystemExit):
            _guard_project_id("clearbag-prod")

    def test_guard_rejects_none(self) -> None:
        """PROJECT_ID 未設定（None）で SystemExit になること。"""
        from scripts.reset_dev_data import _guard_project_id

        with pytest.raises(SystemExit):
            _guard_project_id(None)


class TestDryRunNoDeletes:
    def test_dry_run_no_firestore_deletes(self) -> None:
        """dry-run 時に Firestore のドキュメント削除が呼ばれないこと。"""
        from scripts.reset_dev_data import cleanup_firestore

        mock_doc = MagicMock()
        mock_db = MagicMock()
        mock_db.collection.return_value.stream.return_value = [mock_doc]

        cleanup_firestore(mock_db, dry_run=True)

        # dry_run=True では _delete_document_recursive が呼ばれないため delete() も呼ばれない
        mock_doc.reference.delete.assert_not_called()

    def test_dry_run_no_gcs_deletes(self) -> None:
        """dry-run 時に GCS の blob.delete() が呼ばれないこと。"""
        from scripts.reset_dev_data import cleanup_gcs

        mock_blob = MagicMock()
        with patch("scripts.reset_dev_data.storage") as mock_storage:
            mock_storage.Client.return_value.bucket.return_value.list_blobs.return_value = [
                mock_blob
            ]
            cleanup_gcs("clearbag-dev-clearbag-uploads-dev", dry_run=True)

        mock_blob.delete.assert_not_called()

    def test_dry_run_no_seed_writes(self) -> None:
        """dry-run 時にシードの Firestore 書き込みが呼ばれないこと。"""
        from scripts.reset_dev_data import seed_demo_data

        mock_db = MagicMock()

        seed_demo_data(mock_db, uid="test-uid", email="test@example.com", dry_run=True)

        mock_db.collection.assert_not_called()


class TestCleanupOnlySkipsSeed:
    def test_cleanup_only_skips_seed(self) -> None:
        """--cleanup-only 時にシード関数が呼ばれないこと。"""
        from scripts import reset_dev_data

        with (
            patch.dict("os.environ", {"PROJECT_ID": "clearbag-dev"}),
            patch.object(reset_dev_data, "_init_firebase"),
            patch.object(
                reset_dev_data, "resolve_uid_by_email", return_value="test-uid"
            ),
            patch.object(reset_dev_data, "firestore") as mock_firestore,
            patch.object(reset_dev_data, "cleanup_firestore") as mock_cleanup,
            patch.object(reset_dev_data, "cleanup_gcs") as mock_gcs,
            patch.object(reset_dev_data, "seed_demo_data") as mock_seed,
        ):
            mock_firestore.Client.return_value = MagicMock()
            sys.argv = [
                "reset_dev_data.py",
                "--email",
                "test@example.com",
                "--cleanup-only",
                "--skip-gcs",
            ]
            reset_dev_data.main()

        mock_cleanup.assert_called_once()
        mock_gcs.assert_not_called()  # --skip-gcs なので呼ばれない
        mock_seed.assert_not_called()


class TestMinimalPdf:
    def test_returns_valid_pdf_bytes(self) -> None:
        """_minimal_pdf が PDF マジックバイトで始まり %%EOF で終わる有効なバイト列を返すこと。"""
        from scripts.reset_dev_data import _minimal_pdf

        result = _minimal_pdf("運動会のおしらせ")

        assert result.startswith(b"%PDF-")
        assert b"%%EOF" in result

    def test_title_embedded_in_metadata(self) -> None:
        """タイトルが UTF-16-BE hex として PDF メタデータに含まれること。"""
        from scripts.reset_dev_data import _minimal_pdf

        result = _minimal_pdf("テスト")

        # "テスト" の UTF-16-BE (BOM付き): FEFF30C630B930B9
        expected_hex = (
            (b"\xfe\xff" + "テスト".encode("utf-16-be")).hex().upper().encode()
        )
        assert expected_hex in result


class TestPdfUploadToGcs:
    def test_pdf_uploaded_when_bucket_provided(self) -> None:
        """bucket_name が指定された場合、各ドキュメントの PDF が GCS にアップロードされること。"""
        from scripts.reset_dev_data import seed_demo_data

        mock_db = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        with patch("scripts.reset_dev_data.storage") as mock_storage:
            mock_storage.Client.return_value.bucket.return_value = mock_bucket
            seed_demo_data(
                mock_db,
                uid="test-uid",
                email="test@example.com",
                dry_run=False,
                bucket_name="test-bucket",
            )

        # ドキュメント4件分のアップロードが呼ばれること（通常2件 + 互換性テスト用2件）
        assert mock_blob.upload_from_string.call_count == 4
        # content_type が application/pdf であること
        for call_args in mock_blob.upload_from_string.call_args_list:
            assert call_args.kwargs["content_type"] == "application/pdf"

    def test_no_gcs_upload_when_bucket_not_provided(self) -> None:
        """bucket_name が None の場合、GCS へのアップロードが呼ばれないこと。"""
        from scripts.reset_dev_data import seed_demo_data

        mock_db = MagicMock()

        with patch("scripts.reset_dev_data.storage") as mock_storage:
            seed_demo_data(
                mock_db,
                uid="test-uid",
                email="test@example.com",
                dry_run=False,
                bucket_name=None,
            )

        mock_storage.Client.assert_not_called()
