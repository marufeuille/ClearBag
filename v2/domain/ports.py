"""Ports - サービスのインターフェース定義（ABC）

各Port（抽象基底クラス）は外部サービスとの契約を定義します。
実装クラス（Adapter）はこれらのABCを継承し、全ての抽象メソッドを実装する必要があります。

Protocol版との比較:
- Protocol: 継承不要だが、実装漏れが使用時まで検出されない
- ABC: 継承必須だが、実装漏れがインスタンス化時に即座に検出される

School Agent v2では全て新規実装のアダプタなので、ABCの方が適切。
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from v2.domain.models import (
    Profile,
    Rule,
    FileInfo,
    DocumentAnalysis,
    EventData,
    TaskData,
)


class ConfigSource(ABC):
    """設定情報の読み込み（Google Sheets等）"""

    @abstractmethod
    def load_profiles(self) -> dict[str, Profile]:
        """プロファイル一覧を読み込む"""
        pass

    @abstractmethod
    def load_rules(self) -> list[Rule]:
        """ルール一覧を読み込む"""
        pass


class FileStorage(ABC):
    """ファイルストレージ操作（Google Drive等）"""

    @abstractmethod
    def list_inbox_files(self) -> list[FileInfo]:
        """Inboxフォルダのファイル一覧を取得"""
        pass

    @abstractmethod
    def download(self, file_id: str) -> bytes:
        """ファイルをダウンロード"""
        pass

    @abstractmethod
    def archive(self, file_id: str, new_name: str) -> None:
        """ファイルをリネームしてArchiveフォルダに移動"""
        pass


class DocumentAnalyzer(ABC):
    """文書解析（Gemini等のLLM）"""

    @abstractmethod
    def analyze(
        self,
        content: bytes,
        mime_type: str,
        profiles: dict[str, Profile],
        rules: list[Rule],
    ) -> DocumentAnalysis:
        """文書を解析して構造化データを抽出"""
        pass


class CalendarService(ABC):
    """カレンダーサービス（Google Calendar等）"""

    @abstractmethod
    def create_event(
        self, calendar_id: str, event: EventData, file_link: str = ""
    ) -> str:
        """イベントを作成。event_id or URLを返す"""
        pass


class TaskService(ABC):
    """タスク管理サービス（Todoist等）"""

    @abstractmethod
    def create_task(self, task: TaskData, file_link: str = "") -> str:
        """タスクを作成。task_idを返す"""
        pass


class Notifier(ABC):
    """通知サービス（Slack, LINE等）"""

    @abstractmethod
    def notify_file_processed(
        self,
        filename: str,
        summary: str,
        events: list[EventData],
        tasks: list[TaskData],
        file_link: str = "",
    ) -> None:
        """ファイル処理完了を通知"""
        pass
