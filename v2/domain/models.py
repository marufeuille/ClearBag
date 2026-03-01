"""ドメインモデル - 外部依存なしのデータ構造"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Category(Enum):
    """文書のカテゴリ"""

    EVENT = "EVENT"
    TASK = "TASK"
    INFO = "INFO"
    IGNORE = "IGNORE"


@dataclass(frozen=True)
class EventData:
    """カレンダーイベントデータ"""

    summary: str  # 例: "[長男] 遠足"
    start: str  # ISO8601: "2025-10-25T08:30:00" or "2025-10-25"
    end: str  # ISO8601: "2025-10-25T15:00:00" or "2025-10-25"
    location: str = ""  # 例: "動物園"
    description: str = ""
    confidence: str = "HIGH"  # "HIGH" | "MEDIUM" | "LOW"


@dataclass(frozen=True)
class TaskData:
    """タスクデータ"""

    title: str  # 例: "同意書の提出"
    due_date: str  # YYYY-MM-DD: "2025-10-10"
    assignee: str = "PARENT"  # "PARENT" | "CHILD"
    note: str = ""  # 例: "署名が必要です"


@dataclass(frozen=True)
class DocumentAnalysis:
    """文書解析結果"""

    summary: str  # 文書要約
    category: Category  # EVENT | TASK | INFO | IGNORE
    related_profile_ids: list[str] = field(default_factory=list)
    events: list[EventData] = field(default_factory=list)
    tasks: list[TaskData] = field(default_factory=list)
    archive_filename: str = ""  # 例: "20251025_遠足_長男.pdf"


@dataclass(frozen=True)
class DocumentRecord:
    """B2C用ドキュメントレコード（Firestoreに永続化）"""

    id: str  # Firestore ドキュメントID
    uid: str  # Firebase Auth ユーザーID
    status: str  # "pending" | "processing" | "completed" | "error"
    content_hash: str  # SHA-256 ── 冪等性チェックのキー
    storage_path: str  # GCS: "uploads/{uid}/{documentId}.pdf"
    original_filename: str
    mime_type: str
    summary: str = ""
    category: str = ""  # "EVENT" | "TASK" | "INFO" | "IGNORE"
    archive_filename: str = ""  # Gemini が生成した意味のあるファイル名
    error_message: str | None = None


@dataclass(frozen=True)
class UserProfile:
    """B2C用ユーザープロファイル（calendar_id不要）"""

    id: str  # Firestore ドキュメントID
    name: str  # 例: "太郎"
    grade: str  # 例: "小3"
    keywords: str  # 例: "サッカー,遠足"


@dataclass(frozen=True)
class FamilyMember:
    """ファミリーメンバー"""

    uid: str  # Firebase Auth UID
    role: str  # "owner" | "member"
    display_name: str
    email: str


@dataclass(frozen=True)
class Invitation:
    """ファミリー招待"""

    id: str  # Firestore ドキュメントID
    email: str  # 招待先メールアドレス
    token: str  # UUID v4（URLに埋め込む）
    status: str  # "pending" | "accepted" | "expired"
    invited_by_uid: str
