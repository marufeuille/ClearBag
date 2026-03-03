"""FirestoreRepository のユニットテスト

Firestore クライアントをモックし、None 値のフォールバック動作を検証する。
"""

from unittest.mock import MagicMock

from v2.adapters.firestore_repository import FirestoreDocumentRepository


def _make_snap(data: dict) -> MagicMock:
    """Firestore DocumentSnapshot のモックを生成する"""
    snap = MagicMock()
    snap.to_dict.return_value = data
    return snap


class TestListEventsNullFallback:
    """list_events() で Firestore の None 値が適切にフォールバックされることを検証"""

    def _make_repo(self, snaps: list) -> FirestoreDocumentRepository:
        """モック Firestore を使った FirestoreDocumentRepository を生成する"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.collection_group.return_value.where.return_value.order_by.return_value = mock_query
        mock_query.stream.return_value = snaps
        return FirestoreDocumentRepository(mock_db)

    def test_location_none_falls_back_to_empty_string(self):
        """location が None の場合、空文字列にフォールバックされる"""
        # Arrange
        snaps = [
            _make_snap(
                {
                    "family_id": "fam1",
                    "summary": "遠足",
                    "start": "2026-04-25",
                    "end": "2026-04-25",
                    "location": None,
                    "description": "自由参加",
                    "confidence": "HIGH",
                }
            )
        ]
        repo = self._make_repo(snaps)

        # Act
        events = repo.list_events("fam1")

        # Assert
        assert len(events) == 1
        assert events[0].location == ""

    def test_description_none_falls_back_to_empty_string(self):
        """description が None の場合、空文字列にフォールバックされる"""
        # Arrange
        snaps = [
            _make_snap(
                {
                    "family_id": "fam1",
                    "summary": "運動会",
                    "start": "2026-05-10",
                    "end": "2026-05-10",
                    "location": "校庭",
                    "description": None,
                    "confidence": "HIGH",
                }
            )
        ]
        repo = self._make_repo(snaps)

        # Act
        events = repo.list_events("fam1")

        # Assert
        assert len(events) == 1
        assert events[0].description == ""

    def test_confidence_none_falls_back_to_high(self):
        """confidence が None の場合、'HIGH' にフォールバックされる"""
        # Arrange
        snaps = [
            _make_snap(
                {
                    "family_id": "fam1",
                    "summary": "保護者会",
                    "start": "2026-06-01",
                    "end": "2026-06-01",
                    "location": "",
                    "description": "",
                    "confidence": None,
                }
            )
        ]
        repo = self._make_repo(snaps)

        # Act
        events = repo.list_events("fam1")

        # Assert
        assert len(events) == 1
        assert events[0].confidence == "HIGH"

    def test_all_nullable_fields_none_returns_valid_event_data(self):
        """全 nullable フィールドが None でも EventData が正しく生成される"""
        # Arrange
        snaps = [
            _make_snap(
                {
                    "family_id": "fam1",
                    "summary": "お知らせ",
                    "start": "2026-07-01",
                    "end": "2026-07-01",
                    "location": None,
                    "description": None,
                    "confidence": None,
                }
            )
        ]
        repo = self._make_repo(snaps)

        # Act
        events = repo.list_events("fam1")

        # Assert
        assert len(events) == 1
        event = events[0]
        assert event.location == ""
        assert event.description == ""
        assert event.confidence == "HIGH"


class TestUpdateTaskCompleted:
    """update_task_completed() のユニットテスト"""

    def _make_repo_and_mock(self, snaps: list):
        """モック Firestore を使った repo と mock_db を返す"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.collection_group.return_value.where.return_value.order_by.return_value = mock_query
        mock_query.stream.return_value = snaps
        repo = FirestoreDocumentRepository(mock_db)
        return repo, mock_db

    def test_found_task_returns_true(self):
        """対象タスクが見つかった場合 True を返し update が呼ばれる"""
        # Arrange
        snap = MagicMock()
        snap.id = "task-1"
        snap.reference = MagicMock()
        repo, _ = self._make_repo_and_mock([snap])

        # Act
        result = repo.update_task_completed("fam1", "task-1", True)

        # Assert
        assert result is True
        snap.reference.update.assert_called_once_with({"completed": True})

    def test_not_found_task_returns_false(self):
        """対象タスクが見つからない場合 False を返す"""
        # Arrange
        snap = MagicMock()
        snap.id = "other-task"
        snap.reference = MagicMock()
        repo, _ = self._make_repo_and_mock([snap])

        # Act
        result = repo.update_task_completed("fam1", "task-1", True)

        # Assert
        assert result is False
        snap.reference.update.assert_not_called()

    def test_empty_stream_returns_false(self):
        """ストリームが空の場合 False を返す"""
        # Arrange
        repo, _ = self._make_repo_and_mock([])

        # Act
        result = repo.update_task_completed("fam1", "task-1", False)

        # Assert
        assert result is False

    def test_order_by_completed_is_called(self):
        """order_by("completed") がクエリチェーンに含まれることを検証"""
        # Arrange
        mock_db = MagicMock()
        mock_where = MagicMock()
        mock_order = MagicMock()
        mock_db.collection_group.return_value.where.return_value = mock_where
        mock_where.order_by.return_value = mock_order
        mock_order.stream.return_value = []
        repo = FirestoreDocumentRepository(mock_db)

        # Act
        repo.update_task_completed("fam1", "task-1", True)

        # Assert
        mock_where.order_by.assert_called_once_with("completed")
