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
    DocumentAnalysis,
    DocumentRecord,
    EventData,
    FileInfo,
    Profile,
    Rule,
    TaskData,
    UserProfile,
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


# ─── B2C 用ポート群 ────────────────────────────────────────────────────────────


class DocumentRepository(ABC):
    """ドキュメントレコードの永続化（Firestore等）"""

    @abstractmethod
    def create(self, uid: str, record: DocumentRecord) -> str:
        """ドキュメントレコードを作成。生成されたIDを返す"""
        pass

    @abstractmethod
    def get(self, uid: str, document_id: str) -> DocumentRecord | None:
        """ドキュメントレコードを取得。存在しない場合はNoneを返す"""
        pass

    @abstractmethod
    def list(self, uid: str) -> list[DocumentRecord]:
        """ユーザーのドキュメント一覧を取得"""
        pass

    @abstractmethod
    def update_status(
        self,
        uid: str,
        document_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """ドキュメントのステータスを更新"""
        pass

    @abstractmethod
    def save_analysis(
        self, uid: str, document_id: str, analysis: DocumentAnalysis
    ) -> None:
        """解析結果（events/tasks）をサブコレクションに保存し、documentのsummary/categoryを更新"""
        pass

    @abstractmethod
    def delete(self, uid: str, document_id: str) -> None:
        """ドキュメントレコードと関連するevents/tasksを削除"""
        pass

    @abstractmethod
    def find_by_content_hash(
        self, uid: str, content_hash: str
    ) -> DocumentRecord | None:
        """コンテンツハッシュで既存レコードを検索（冪等性チェック用）"""
        pass

    @abstractmethod
    def list_events(
        self,
        uid: str,
        from_date: str | None = None,
        to_date: str | None = None,
        profile_id: str | None = None,
    ) -> list[EventData]:
        """日付範囲でイベントを取得"""
        pass

    @abstractmethod
    def list_tasks(self, uid: str, completed: bool | None = None) -> list[TaskData]:
        """タスク一覧を取得。completedフィルターはオプション"""
        pass

    @abstractmethod
    def update_task_completed(self, uid: str, task_id: str, completed: bool) -> None:
        """タスクの完了状態を更新"""
        pass


class UserConfigRepository(ABC):
    """ユーザー設定・プロファイルの永続化（Firestore等）"""

    @abstractmethod
    def get_user(self, uid: str) -> dict:
        """ユーザー設定を取得（plan, documentsThisMonth, icalToken等）"""
        pass

    @abstractmethod
    def update_user(self, uid: str, data: dict) -> None:
        """ユーザー設定を更新"""
        pass

    @abstractmethod
    def list_profiles(self, uid: str) -> list[UserProfile]:
        """ユーザーのプロファイル一覧を取得"""
        pass

    @abstractmethod
    def create_profile(self, uid: str, profile: UserProfile) -> str:
        """プロファイルを作成。生成されたIDを返す"""
        pass

    @abstractmethod
    def update_profile(self, uid: str, profile_id: str, profile: UserProfile) -> None:
        """プロファイルを更新"""
        pass

    @abstractmethod
    def delete_profile(self, uid: str, profile_id: str) -> None:
        """プロファイルを削除"""
        pass


class BlobStorage(ABC):
    """バイナリファイルのアップロード・ダウンロード（GCS等）"""

    @abstractmethod
    def upload(self, blob_path: str, content: bytes, content_type: str) -> str:
        """ファイルをアップロード。ストレージパス（blob_path）を返す"""
        pass

    @abstractmethod
    def download(self, blob_path: str) -> bytes:
        """ファイルをダウンロードしてバイト列を返す"""
        pass

    @abstractmethod
    def delete(self, blob_path: str) -> None:
        """ファイルを削除"""
        pass


class TaskQueue(ABC):
    """非同期処理キュー（Cloud Tasks等）"""

    @abstractmethod
    def enqueue(self, payload: dict) -> str:
        """ジョブをキューに追加。キュータスクIDを返す"""
        pass


class CalendarFeedRenderer(ABC):
    """iCalフィードのレンダリング"""

    @abstractmethod
    def render(self, events: list[EventData]) -> str:
        """EventDataのリストからiCal形式の文字列を生成"""
        pass
