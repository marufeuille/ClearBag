"""ドメインモデルのテスト"""

import pytest

from v2.domain.models import (
    Category,
    DocumentAnalysis,
    EventData,
    FileInfo,
    ProcessingResult,
    Profile,
    Rule,
    TaskData,
)


class TestCategory:
    """Category enum のテスト"""

    def test_category_values(self):
        """全てのカテゴリ値が定義されている"""
        assert Category.EVENT.value == "EVENT"
        assert Category.TASK.value == "TASK"
        assert Category.INFO.value == "INFO"
        assert Category.IGNORE.value == "IGNORE"


class TestProfile:
    """Profile dataclass のテスト"""

    def test_create_profile(self):
        """Profileが正しく生成される"""
        profile = Profile(
            id="CHILD1",
            name="太郎",
            grade="小3",
            keywords="サッカー",
            calendar_id="cal123",
        )
        assert profile.id == "CHILD1"
        assert profile.name == "太郎"
        assert profile.grade == "小3"

    def test_profile_is_frozen(self):
        """Profileは不変（frozen）である"""
        profile = Profile(id="CHILD1", name="太郎", grade="小3", keywords="", calendar_id="")
        with pytest.raises(AttributeError):
            profile.name = "花子"  # type: ignore


class TestRule:
    """Rule dataclass のテスト"""

    def test_create_rule(self):
        """Ruleが正しく生成される"""
        rule = Rule(
            rule_id="R001",
            target_profile="ALL",
            rule_type="REMINDER",
            content="3日前に通知",
        )
        assert rule.rule_id == "R001"
        assert rule.target_profile == "ALL"


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


class TestFileInfo:
    """FileInfo dataclass のテスト"""

    def test_create_file_info(self):
        """FileInfoが正しく生成される"""
        file_info = FileInfo(
            id="file123",
            name="test.pdf",
            mime_type="application/pdf",
            web_view_link="https://example.com",
        )
        assert file_info.id == "file123"
        assert file_info.name == "test.pdf"


class TestProcessingResult:
    """ProcessingResult dataclass のテスト"""

    def test_create_result_success(self):
        """成功時のProcessingResultが生成される"""
        file_info = FileInfo(id="f1", name="test.pdf", mime_type="application/pdf")
        analysis = DocumentAnalysis(summary="テスト", category=Category.EVENT)

        result = ProcessingResult(
            file_info=file_info,
            analysis=analysis,
            events_created=2,
            tasks_created=1,
            notification_sent=True,
            archived=True,
        )
        assert result.events_created == 2
        assert result.archived is True
        assert result.error is None

    def test_create_result_error(self):
        """エラー時のProcessingResultが生成される"""
        file_info = FileInfo(id="f1", name="test.pdf", mime_type="application/pdf")

        result = ProcessingResult(file_info=file_info, error="Download failed")
        assert result.error == "Download failed"
        assert result.archived is False
        assert result.analysis is None
