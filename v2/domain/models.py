"""ドメインモデル - 外部依存なしのデータ構造"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Category(Enum):
    """文書のカテゴリ"""
    EVENT = "EVENT"
    TASK = "TASK"
    INFO = "INFO"
    IGNORE = "IGNORE"


@dataclass(frozen=True)
class Profile:
    """家族メンバーのプロファイル"""
    id: str              # 例: "CHILD1"
    name: str            # 例: "太郎"
    grade: str           # 例: "小3"
    keywords: str        # 例: "サッカー,遠足"
    calendar_id: str     # 例: "c_abc123@group.calendar.google.com"


@dataclass(frozen=True)
class Rule:
    """処理ルール"""
    rule_id: str         # 例: "R001"
    target_profile: str  # 例: "CHILD1" or "ALL"
    rule_type: str       # 例: "REMINDER", "IGNORE", "NAMING"
    content: str         # 例: "持ち物が必要なイベントは3日前にタスク期限を設定"


@dataclass(frozen=True)
class EventData:
    """カレンダーイベントデータ"""
    summary: str         # 例: "[長男] 遠足"
    start: str           # ISO8601: "2025-10-25T08:30:00" or "2025-10-25"
    end: str             # ISO8601: "2025-10-25T15:00:00" or "2025-10-25"
    location: str = ""   # 例: "動物園"
    description: str = ""
    confidence: str = "HIGH"  # "HIGH" | "MEDIUM" | "LOW"


@dataclass(frozen=True)
class TaskData:
    """タスクデータ"""
    title: str           # 例: "同意書の提出"
    due_date: str        # YYYY-MM-DD: "2025-10-10"
    assignee: str = "PARENT"  # "PARENT" | "CHILD"
    note: str = ""       # 例: "署名が必要です"


@dataclass(frozen=True)
class DocumentAnalysis:
    """文書解析結果"""
    summary: str                                    # 文書要約
    category: Category                              # EVENT | TASK | INFO | IGNORE
    related_profile_ids: list[str] = field(default_factory=list)
    events: list[EventData] = field(default_factory=list)
    tasks: list[TaskData] = field(default_factory=list)
    archive_filename: str = ""                      # 例: "20251025_遠足_長男.pdf"


@dataclass(frozen=True)
class FileInfo:
    """Google Driveファイル情報"""
    id: str              # Google Drive file ID
    name: str            # 元のファイル名
    mime_type: str       # 例: "application/pdf"
    web_view_link: str = ""


@dataclass(frozen=True)
class ProcessingResult:
    """各ファイル処理の結果。テストや冪等性チェックに利用。"""
    file_info: FileInfo
    analysis: Optional[DocumentAnalysis] = None
    events_created: int = 0
    tasks_created: int = 0
    notification_sent: bool = False
    archived: bool = False
    error: Optional[str] = None
