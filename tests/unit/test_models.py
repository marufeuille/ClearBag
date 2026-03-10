"""ドメインモデルのテスト"""

import pytest
from v2.domain.models import (
    Category,
    CostInfo,
    DocumentAnalysis,
    DocumentExtras,
    DocumentRecord,
    EventData,
    PrepItem,
    TaskData,
    UserProfile,
)


class TestCategory:
    """Category enum のテスト"""

    def test_category_values(self):
        """全てのカテゴリ値が定義されている"""
        assert Category.EVENT.value == "EVENT"
        assert Category.TASK.value == "TASK"
        assert Category.INFO.value == "INFO"
        assert Category.IGNORE.value == "IGNORE"


class TestEventData:
    """EventData dataclass のテスト"""

    def test_create_event_with_defaults(self):
        """デフォルト値でEventDataが生成される"""
        event = EventData(summary="遠足", start="2026-04-25", end="2026-04-25")
        assert event.summary == "遠足"
        assert event.location == ""
        assert event.description == ""
        assert event.confidence == "HIGH"

    def test_create_event_all_fields(self):
        """全フィールド指定でEventDataが生成される"""
        event = EventData(
            summary="遠足",
            start="2026-04-25T08:00:00",
            end="2026-04-25T15:00:00",
            location="動物園",
            description="お弁当持参",
            confidence="MEDIUM",
        )
        assert event.location == "動物園"
        assert event.confidence == "MEDIUM"


class TestTaskData:
    """TaskData dataclass のテスト"""

    def test_create_task_with_defaults(self):
        """デフォルト値でTaskDataが生成される"""
        task = TaskData(title="提出物", due_date="2026-04-20")
        assert task.title == "提出物"
        assert task.assignee == "PARENT"
        assert task.note == ""

    def test_create_task_all_fields(self):
        """全フィールド指定でTaskDataが生成される"""
        task = TaskData(
            title="提出物",
            due_date="2026-04-20",
            assignee="CHILD",
            note="署名必要",
        )
        assert task.assignee == "CHILD"
        assert task.note == "署名必要"


class TestDocumentAnalysis:
    """DocumentAnalysis dataclass のテスト"""

    def test_create_analysis_minimal(self):
        """最小限のフィールドでDocumentAnalysisが生成される"""
        analysis = DocumentAnalysis(summary="テスト文書", category=Category.INFO)
        assert analysis.summary == "テスト文書"
        assert analysis.category == Category.INFO
        assert analysis.related_profile_ids == []
        assert analysis.events == []
        assert analysis.tasks == []

    def test_create_analysis_full(self):
        """全フィールド指定でDocumentAnalysisが生成される"""
        event = EventData(summary="イベント", start="2026-04-25", end="2026-04-25")
        task = TaskData(title="タスク", due_date="2026-04-20")

        analysis = DocumentAnalysis(
            summary="テスト",
            category=Category.EVENT,
            related_profile_ids=["CHILD1"],
            events=[event],
            tasks=[task],
            archive_filename="20260425_test.pdf",
        )
        assert len(analysis.events) == 1
        assert len(analysis.tasks) == 1
        assert analysis.archive_filename == "20260425_test.pdf"


class TestDocumentRecord:
    """DocumentRecord dataclass のテスト"""

    def test_create_document_record_minimal(self):
        """最小限のフィールドで DocumentRecord が生成される"""
        record = DocumentRecord(
            id="doc_001",
            uid="user_abc",
            status="pending",
            content_hash="abc123",
            storage_path="uploads/user_abc/doc_001.pdf",
            original_filename="遠足のお知らせ.pdf",
            mime_type="application/pdf",
        )
        assert record.id == "doc_001"
        assert record.uid == "user_abc"
        assert record.status == "pending"
        assert record.summary == ""
        assert record.category == ""
        assert record.error_message is None

    def test_create_document_record_completed(self):
        """解析完了状態の DocumentRecord が生成される"""
        record = DocumentRecord(
            id="doc_002",
            uid="user_abc",
            status="completed",
            content_hash="def456",
            storage_path="uploads/user_abc/doc_002.pdf",
            original_filename="行事予定.pdf",
            mime_type="application/pdf",
            summary="4月の行事一覧です。",
            category="EVENT",
        )
        assert record.status == "completed"
        assert record.summary == "4月の行事一覧です。"
        assert record.category == "EVENT"

    def test_document_record_is_frozen(self):
        """DocumentRecord は不変（frozen）である"""
        record = DocumentRecord(
            id="doc_003",
            uid="u",
            status="pending",
            content_hash="x",
            storage_path="p",
            original_filename="f.pdf",
            mime_type="application/pdf",
        )
        with pytest.raises(AttributeError):
            record.status = "completed"  # type: ignore


class TestPrepItem:
    """PrepItem dataclass のテスト"""

    def test_create_prep_item_with_defaults(self):
        """デフォルト値でPrepItemが生成される"""
        item = PrepItem(item="水筒")
        assert item.item == "水筒"
        assert item.event_index == -1
        assert item.source_text == ""

    def test_create_prep_item_with_event_index(self):
        """event_indexを指定してPrepItemが生成される"""
        item = PrepItem(item="体操服", event_index=0, source_text="体操服を着てきてください")
        assert item.event_index == 0
        assert item.source_text == "体操服を着てきてください"

    def test_prep_item_is_frozen(self):
        """PrepItem は不変（frozen）である"""
        item = PrepItem(item="水筒")
        with pytest.raises(AttributeError):
            item.item = "弁当"  # type: ignore


class TestCostInfo:
    """CostInfo dataclass のテスト"""

    def test_create_cost_info_with_defaults(self):
        """デフォルト値でCostInfoが生成される"""
        cost = CostInfo(description="遠足代")
        assert cost.description == "遠足代"
        assert cost.amount is None
        assert cost.due_date == ""
        assert cost.source_text == ""

    def test_create_cost_info_with_amount(self):
        """金額付きCostInfoが生成される"""
        cost = CostInfo(description="教材費", amount=1500, due_date="2026-04-20")
        assert cost.amount == 1500
        assert cost.due_date == "2026-04-20"

    def test_cost_info_is_frozen(self):
        """CostInfo は不変（frozen）である"""
        cost = CostInfo(description="遠足代")
        with pytest.raises(AttributeError):
            cost.amount = 500  # type: ignore


class TestDocumentExtras:
    """DocumentExtras dataclass のテスト"""

    def test_create_extras_with_defaults(self):
        """デフォルト値でDocumentExtrasが生成される"""
        extras = DocumentExtras()
        assert extras.items_to_bring == []
        assert extras.dress_code == []
        assert extras.costs == []
        assert extras.notes == []
        assert extras.source_texts == []

    def test_create_extras_full(self):
        """全フィールド指定でDocumentExtrasが生成される"""
        extras = DocumentExtras(
            items_to_bring=[PrepItem(item="水筒"), PrepItem(item="レジャーシート", event_index=0)],
            dress_code=["体操服", "白い靴下"],
            costs=[CostInfo(description="遠足代", amount=500, due_date="2026-04-20")],
            notes=["雨天中止"],
            source_texts=["水筒をお持ちください"],
        )
        assert len(extras.items_to_bring) == 2
        assert extras.items_to_bring[1].event_index == 0
        assert extras.dress_code == ["体操服", "白い靴下"]
        assert extras.costs[0].amount == 500
        assert extras.notes == ["雨天中止"]

    def test_extras_is_frozen(self):
        """DocumentExtras は不変（frozen）である"""
        extras = DocumentExtras()
        with pytest.raises(AttributeError):
            extras.notes = ["変更"]  # type: ignore


class TestDocumentAnalysisWithExtras:
    """DocumentAnalysis の extras フィールドのテスト"""

    def test_analysis_extras_defaults_to_none(self):
        """extrasのデフォルト値はNone（後方互換）"""
        analysis = DocumentAnalysis(summary="テスト", category=Category.INFO)
        assert analysis.extras is None

    def test_analysis_with_extras(self):
        """extrasを指定してDocumentAnalysisが生成される"""
        extras = DocumentExtras(
            items_to_bring=[PrepItem(item="水筒")],
            notes=["雨天中止"],
        )
        analysis = DocumentAnalysis(
            summary="遠足のお知らせ",
            category=Category.EVENT,
            extras=extras,
        )
        assert analysis.extras is not None
        assert analysis.extras.items_to_bring[0].item == "水筒"
        assert analysis.extras.notes == ["雨天中止"]


class TestUserProfile:
    """UserProfile dataclass のテスト"""

    def test_create_user_profile(self):
        """UserProfile が正しく生成される"""
        profile = UserProfile(
            id="profile_001",
            name="太郎",
            grade="小3",
            keywords="サッカー,遠足",
        )
        assert profile.id == "profile_001"
        assert profile.name == "太郎"
        assert profile.grade == "小3"
        assert profile.keywords == "サッカー,遠足"

    def test_user_profile_has_no_calendar_id(self):
        """UserProfile は calendar_id フィールドを持たない（B2C設計）"""
        profile = UserProfile(id="p1", name="花子", grade="小1", keywords="")
        assert not hasattr(profile, "calendar_id")

    def test_user_profile_is_frozen(self):
        """UserProfile は不変（frozen）である"""
        profile = UserProfile(id="p1", name="太郎", grade="小3", keywords="")
        with pytest.raises(AttributeError):
            profile.name = "花子"  # type: ignore
