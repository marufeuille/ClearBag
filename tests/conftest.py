"""共通テストフィクスチャ

全テストから利用可能なモックオブジェクトとサンプルデータを提供。

モックの作成:
- MagicMock(spec=ABC) でABCのメソッドシグネチャを保持
- Protocol時代と同じ書き方でOK
"""

from unittest.mock import MagicMock

import pytest
from v2.domain.models import (
    Category,
    DocumentAnalysis,
    EventData,
    FileInfo,
    Profile,
    Rule,
    TaskData,
)
from v2.domain.ports import (
    CalendarService,
    ConfigSource,
    DocumentAnalyzer,
    FileStorage,
    Notifier,
    TaskService,
)

# ========== サンプルデータ ==========


@pytest.fixture
def sample_profile_child1() -> Profile:
    """サンプルプロファイル: 子供1"""
    return Profile(
        id="CHILD1",
        name="太郎",
        grade="小3",
        keywords="サッカー,遠足",
        calendar_id="calendar_child1@example.com",
    )


@pytest.fixture
def sample_profile_child2() -> Profile:
    """サンプルプロファイル: 子供2"""
    return Profile(
        id="CHILD2",
        name="花子",
        grade="小1",
        keywords="ダンス",
        calendar_id="calendar_child2@example.com",
    )


@pytest.fixture
def sample_profiles(sample_profile_child1, sample_profile_child2) -> dict[str, Profile]:
    """サンプルプロファイル辞書"""
    return {
        "CHILD1": sample_profile_child1,
        "CHILD2": sample_profile_child2,
    }


@pytest.fixture
def sample_rule() -> Rule:
    """サンプルルール"""
    return Rule(
        rule_id="R001",
        target_profile="ALL",
        rule_type="REMINDER",
        content="持ち物が必要なイベントは3日前にタスク期限を設定する",
    )


@pytest.fixture
def sample_file_info() -> FileInfo:
    """サンプルファイル情報"""
    return FileInfo(
        id="file_123",
        name="遠足のお知らせ.pdf",
        mime_type="application/pdf",
        web_view_link="https://drive.google.com/file/d/file_123/view",
    )


@pytest.fixture
def sample_event_high() -> EventData:
    """サンプルイベント（HIGH confidence）"""
    return EventData(
        summary="[長男] 遠足",
        start="2026-04-25T08:30:00",
        end="2026-04-25T15:00:00",
        location="動物園",
        description="お弁当・水筒持参",
        confidence="HIGH",
    )


@pytest.fixture
def sample_event_low() -> EventData:
    """サンプルイベント（LOW confidence）"""
    return EventData(
        summary="[メモ] 持ち物確認",
        start="2026-04-24",
        end="2026-04-24",
        confidence="LOW",
    )


@pytest.fixture
def sample_task() -> TaskData:
    """サンプルタスク"""
    return TaskData(
        title="同意書の提出",
        due_date="2026-04-20",
        assignee="PARENT",
        note="署名が必要です",
    )


@pytest.fixture
def sample_analysis(
    sample_event_high, sample_event_low, sample_task
) -> DocumentAnalysis:
    """サンプル解析結果"""
    return DocumentAnalysis(
        summary="遠足のお知らせです。4月25日に動物園へ行きます。",
        category=Category.EVENT,
        related_profile_ids=["CHILD1"],
        events=[sample_event_high, sample_event_low],
        tasks=[sample_task],
        archive_filename="20260425_遠足_長男.pdf",
    )


# ========== モックフィクスチャ ==========


@pytest.fixture
def mock_config(sample_profiles, sample_rule) -> MagicMock:
    """ConfigSource のモック"""
    mock = MagicMock(spec=ConfigSource)
    mock.load_profiles.return_value = sample_profiles
    mock.load_rules.return_value = [sample_rule]
    return mock


@pytest.fixture
def mock_storage(sample_file_info) -> MagicMock:
    """FileStorage のモック"""
    mock = MagicMock(spec=FileStorage)
    mock.list_inbox_files.return_value = [sample_file_info]
    mock.download.return_value = b"fake-pdf-content"
    return mock


@pytest.fixture
def mock_analyzer(sample_analysis) -> MagicMock:
    """DocumentAnalyzer のモック"""
    mock = MagicMock(spec=DocumentAnalyzer)
    mock.analyze.return_value = sample_analysis
    return mock


@pytest.fixture
def mock_calendar() -> MagicMock:
    """CalendarService のモック"""
    mock = MagicMock(spec=CalendarService)
    mock.create_event.return_value = "event_123"
    return mock


@pytest.fixture
def mock_task_service() -> MagicMock:
    """TaskService のモック"""
    mock = MagicMock(spec=TaskService)
    mock.create_task.return_value = "task_456"
    return mock


@pytest.fixture
def mock_notifier() -> MagicMock:
    """Notifier のモック"""
    mock = MagicMock(spec=Notifier)
    return mock
