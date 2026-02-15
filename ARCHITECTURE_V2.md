# School Agent v2 アーキテクチャ設計書

## 目次
1. [概要](#概要)
2. [設計原則](#設計原則)
3. [アーキテクチャパターン](#アーキテクチャパターン)
4. [ディレクトリ構造](#ディレクトリ構造)
5. [ドメインモデル](#ドメインモデル)
6. [Ports（インターフェース）](#portsインターフェース)
7. [サービス層](#サービス層)
8. [テスト戦略](#テスト戦略)
9. [実装フェーズ](#実装フェーズ)

---

## 概要

School Agent v2は、既存のモノリシックなコード（`src/`）をHexagonal Architecture（ヘキサゴナルアーキテクチャ）でリファクタリングしたものです。

### 目的
- **テスト容易性**: 外部APIなしでビジネスロジックをテスト可能
- **拡張容易性**: 通知先の変更（Slack→LINE等）がインターフェース差し替えで対応可能
- **LLMとの協調**: テストベースの対話で開発可能な構造
- **既存コードとの併存**: `src/` は一切変更せず `v2/` に新コードを配置

### 既存コードの問題点
- ✗ 外部APIに直接依存（Google Drive, Gemini, Calendar, Todoist, Slack）
- ✗ テストが存在しない
- ✗ 認証情報を毎回再生成
- ✗ エラーハンドリングが弱い（`print` のみ）
- ✗ core.py と main.py の重複
- ✗ 冪等性がない

---

## 設計原則

### 1. Dependency Inversion（依存性逆転）
ビジネスロジックは具象クラス（Google Drive APIクライアント等）に依存せず、抽象インターフェース（Protocol）に依存する。

```python
# ❌ 悪い例（既存コード）
from googleapiclient.discovery import build

def process_files():
    service = build('drive', 'v3', credentials=...)  # 具象クラスに直接依存
    files = service.files().list(...).execute()

# ✅ 良い例（v2）
def process_files(file_storage: FileStorage):  # Protocolに依存
    files = file_storage.list_inbox_files()
```

### 2. Testability First（テスト第一）
全てのビジネスロジックは外部APIなしでテスト可能。

```python
# テスト時はモックを注入
orchestrator = Orchestrator(
    config_source=MockConfigSource(),
    file_storage=MockFileStorage(),
    analyzer=MockAnalyzer(),
    action_dispatcher=MockDispatcher(),
)
results = orchestrator.run()
assert results[0].archived is True
```

### 3. Immutability（不変性）
ドメインモデルは全て `frozen dataclass` で不変。

```python
@dataclass(frozen=True)
class EventData:
    summary: str
    start: str
    end: str
    # フィールドは作成後変更不可
```

### 4. Single Responsibility（単一責任）
各クラスは1つの責務のみを持つ。

- `Orchestrator`: ワークフロー全体の統合
- `ActionDispatcher`: 解析結果→アクション振り分け
- 各Adapter: 1つの外部サービスとの通信のみ

---

## アーキテクチャパターン

### Hexagonal Architecture（Ports & Adapters）

```
┌─────────────────────────────────────────────────────────┐
│                      Entrypoints                         │
│                  (CLI, Cloud Functions)                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│                     Services Layer                       │
│          (Orchestrator, ActionDispatcher)                │
│              ▲                        ▲                  │
│              │                        │                  │
│         depends on              depends on               │
│              │                        │                  │
│              ▼                        ▼                  │
│        Domain Models               Ports                 │
│      (dataclass)              (Protocol interfaces)      │
└──────────────────────────────────────┬──────────────────┘
                                       │
                                  implements
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────┐
│                    Adapters Layer                        │
│   (GoogleDrive, Gemini, Calendar, Todoist, Slack)        │
│              (外部APIとの具体的な通信)                    │
└─────────────────────────────────────────────────────────┘
```

**ポイント**:
- **Services層** は **Ports（Protocol）** にのみ依存
- **Adapters層** は **Ports** を実装
- テスト時は Adapters をモックに差し替える

---

## ディレクトリ構造

```
school_ai_app/
├── src/                          # 既存コード（一切変更しない）
│   └── ...
│
├── v2/                           # 新アーキテクチャ
│   ├── __init__.py
│   ├── domain/                   # ドメイン層
│   │   ├── __init__.py
│   │   ├── models.py             # dataclass定義
│   │   ├── errors.py             # ドメイン例外
│   │   └── ports.py              # Protocol定義
│   │
│   ├── services/                 # ビジネスロジック層
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # メインワークフロー
│   │   └── action_dispatcher.py  # アクション振り分け
│   │
│   ├── adapters/                 # アダプタ層（Phase 3以降）
│   │   ├── __init__.py
│   │   ├── google_drive.py
│   │   ├── google_calendar.py
│   │   ├── gemini.py
│   │   ├── todoist.py
│   │   ├── slack.py
│   │   └── credentials.py
│   │
│   ├── entrypoints/              # エントリポイント（Phase 4以降）
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── cloud_function.py
│   │   └── factory.py
│   │
│   └── config.py                 # 設定管理
│
├── tests/                        # テスト
│   ├── __init__.py
│   ├── conftest.py               # 共通fixture
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_orchestrator.py
│   │   └── test_action_dispatcher.py
│   ├── integration/              # Phase 4以降
│   └── contract/                 # Phase 4以降
│
└── ARCHITECTURE_V2.md            # 本ドキュメント
```

---

## ドメインモデル

全て `dataclass(frozen=True)` で定義。外部依存なし。

### Profile
```python
@dataclass(frozen=True)
class Profile:
    id: str              # 例: "CHILD1"
    name: str            # 例: "太郎"
    grade: str           # 例: "小3"
    keywords: str        # 例: "サッカー,遠足"
    calendar_id: str     # 例: "c_abc123@group.calendar.google.com"
```

### Rule
```python
@dataclass(frozen=True)
class Rule:
    rule_id: str         # 例: "R001"
    target_profile: str  # 例: "CHILD1" or "ALL"
    rule_type: str       # 例: "REMINDER", "IGNORE", "NAMING"
    content: str         # 例: "持ち物が必要なイベントは3日前にタスク期限を設定"
```

### EventData
```python
@dataclass(frozen=True)
class EventData:
    summary: str         # 例: "[長男] 遠足"
    start: str           # ISO8601: "2025-10-25T08:30:00" or "2025-10-25"
    end: str             # ISO8601: "2025-10-25T15:00:00" or "2025-10-25"
    location: str = ""   # 例: "動物園"
    description: str = ""
    confidence: str = "HIGH"  # "HIGH" | "MEDIUM" | "LOW"
```

### TaskData
```python
@dataclass(frozen=True)
class TaskData:
    title: str           # 例: "同意書の提出"
    due_date: str        # YYYY-MM-DD: "2025-10-10"
    assignee: str = "PARENT"  # "PARENT" | "CHILD"
    note: str = ""       # 例: "署名が必要です"
```

### DocumentAnalysis
```python
@dataclass(frozen=True)
class DocumentAnalysis:
    summary: str                          # 文書要約
    category: Category                    # EVENT | TASK | INFO | IGNORE
    related_profile_ids: list[str] = field(default_factory=list)
    events: list[EventData] = field(default_factory=list)
    tasks: list[TaskData] = field(default_factory=list)
    archive_filename: str = ""            # 例: "20251025_遠足_長男.pdf"
```

### FileInfo
```python
@dataclass(frozen=True)
class FileInfo:
    id: str              # Google Drive file ID
    name: str            # 元のファイル名
    mime_type: str       # 例: "application/pdf"
    web_view_link: str = ""
```

### ProcessingResult
```python
@dataclass(frozen=True)
class ProcessingResult:
    """各ファイル処理の結果"""
    file_info: FileInfo
    analysis: Optional[DocumentAnalysis] = None
    events_created: int = 0
    tasks_created: int = 0
    notification_sent: bool = False
    archived: bool = False
    error: Optional[str] = None
```

---

## Ports（インターフェース）

全て `ABC (Abstract Base Class)` で定義。実装クラスは継承が必須で、実装漏れがインスタンス化時に即座に検出される。

### ConfigSource
```python
class ConfigSource(ABC):
    @abstractmethod
    def load_profiles(self) -> dict[str, Profile]: ...

    @abstractmethod
    def load_rules(self) -> list[Rule]: ...
```

### FileStorage
```python
class FileStorage(ABC):
    @abstractmethod
    def list_inbox_files(self) -> list[FileInfo]: ...

    @abstractmethod
    def download(self, file_id: str) -> bytes: ...

    @abstractmethod
    def archive(self, file_id: str, new_name: str) -> None: ...
```

### DocumentAnalyzer
```python
class DocumentAnalyzer(ABC):
    @abstractmethod
    def analyze(
        self,
        content: bytes,
        mime_type: str,
        profiles: dict[str, Profile],
        rules: list[Rule],
    ) -> DocumentAnalysis: ...
```

### CalendarService
```python
class CalendarService(ABC):
    @abstractmethod
    def create_event(
        self, calendar_id: str, event: EventData, file_link: str = ""
    ) -> str: ...  # returns event_id or URL
```

### TaskService
```python
class TaskService(ABC):
    @abstractmethod
    def create_task(
        self, task: TaskData, file_link: str = ""
    ) -> str: ...  # returns task_id
```

### Notifier
```python
class Notifier(ABC):
    @abstractmethod
    def notify_file_processed(
        self,
        filename: str,
        summary: str,
        events: list[EventData],
        tasks: list[TaskData],
        file_link: str = "",
    ) -> None: ...
```

---

## サービス層

### Orchestrator

メインワークフロー。既存 `core.py` の責務を再設計。

```python
class Orchestrator:
    def __init__(
        self,
        config_source: ConfigSource,
        file_storage: FileStorage,
        analyzer: DocumentAnalyzer,
        action_dispatcher: ActionDispatcher,
    ) -> None:
        self._config = config_source
        self._storage = file_storage
        self._analyzer = analyzer
        self._dispatcher = action_dispatcher

    def run(self) -> list[ProcessingResult]:
        """Inboxの全ファイルを処理"""
        profiles = self._config.load_profiles()
        rules = self._config.load_rules()
        files = self._storage.list_inbox_files()

        results: list[ProcessingResult] = []
        for file_info in files:
            result = self._process_single(file_info, profiles, rules)
            results.append(result)

        return results

    def _process_single(
        self, file_info, profiles, rules
    ) -> ProcessingResult:
        """1ファイルの処理（エラーハンドリング込み）"""
        try:
            content = self._storage.download(file_info.id)
            analysis = self._analyzer.analyze(
                content, file_info.mime_type, profiles, rules
            )
            dispatch_result = self._dispatcher.dispatch(
                file_info, analysis, profiles
            )
            archive_name = analysis.archive_filename or f"PROCESSED_{file_info.name}"
            self._storage.archive(file_info.id, archive_name)

            return ProcessingResult(
                file_info=file_info,
                analysis=analysis,
                events_created=dispatch_result.events_created,
                tasks_created=dispatch_result.tasks_created,
                notification_sent=dispatch_result.notification_sent,
                archived=True,
            )
        except Exception as e:
            logger.exception("Error processing %s", file_info.name)
            return ProcessingResult(
                file_info=file_info, error=str(e)
            )
```

### ActionDispatcher

解析結果からアクション実行への振り分け。

```python
class ActionDispatcher:
    def __init__(
        self,
        calendar: CalendarService,
        task_service: TaskService,
        notifier: Notifier,
    ) -> None:
        self._calendar = calendar
        self._task_service = task_service
        self._notifier = notifier

    def dispatch(
        self,
        file_info: FileInfo,
        analysis: DocumentAnalysis,
        profiles: dict[str, Profile],
    ) -> DispatchResult:
        result = DispatchResult()

        # Calendar events (LOW confidence は除外)
        eligible_events = [
            e for e in analysis.events if e.confidence != "LOW"
        ]
        for event in eligible_events:
            calendar_id = self._resolve_calendar_id(
                analysis.related_profile_ids, profiles
            )
            self._calendar.create_event(
                calendar_id, event, file_info.web_view_link
            )
            result.events_created += 1

        # Tasks
        for task in analysis.tasks:
            self._task_service.create_task(task, file_info.web_view_link)
            result.tasks_created += 1

        # Notification
        self._notifier.notify_file_processed(
            filename=file_info.name,
            summary=analysis.summary,
            events=eligible_events,
            tasks=analysis.tasks,
            file_link=file_info.web_view_link,
        )
        result.notification_sent = True

        return result

    @staticmethod
    def _resolve_calendar_id(
        related_ids: list[str], profiles: dict[str, Profile]
    ) -> str:
        """ProfileIDからカレンダーIDを解決。見つからない場合はprimary"""
        for pid in related_ids:
            if pid in profiles and profiles[pid].calendar_id:
                return profiles[pid].calendar_id
        return "primary"
```

---

## テスト戦略

### テストピラミッド

```
          /\
         /  \     Contract Tests (LLM出力スキーマ検証) - Phase 4
        /----\
       /      \   Integration Tests (モックで結合テスト) - Phase 4
      /--------\
     /          \  Unit Tests (各クラス単体テスト) - Phase 1-2 ★
    /____________\
```

### Phase 1-2: Unit Tests

**原則**: 外部APIは一切呼ばない。全てモック。

#### test_models.py
- dataclass生成テスト
- frozen制約テスト（変更不可の確認）
- Category enumのバリデーション

#### test_orchestrator.py
```python
def test_orchestrator_processes_single_file(
    mock_config, mock_storage, mock_analyzer, mock_dispatcher
):
    """ファイル1件の正常処理フロー"""
    mock_storage.list_inbox_files.return_value = [
        FileInfo(id="f1", name="test.pdf", mime_type="application/pdf")
    ]
    mock_storage.download.return_value = b"pdf-bytes"
    mock_analyzer.analyze.return_value = DocumentAnalysis(
        summary="テスト文書", category=Category.EVENT
    )

    orch = Orchestrator(mock_config, mock_storage, mock_analyzer, mock_dispatcher)
    results = orch.run()

    assert len(results) == 1
    assert results[0].archived is True
    assert results[0].error is None
    mock_storage.archive.assert_called_once()
```

#### test_action_dispatcher.py
```python
def test_low_confidence_events_are_filtered():
    """confidence=LOW のイベントはカレンダーに登録しない"""
    analysis = DocumentAnalysis(
        summary="test",
        category=Category.EVENT,
        events=[
            EventData(summary="遠足", start="2026-04-01", end="2026-04-01", confidence="HIGH"),
            EventData(summary="メモ", start="2026-04-02", end="2026-04-02", confidence="LOW"),
        ],
    )
    dispatcher = ActionDispatcher(mock_calendar, mock_task, mock_notifier)
    result = dispatcher.dispatch(file_info, analysis, profiles)

    assert result.events_created == 1
    assert mock_calendar.create_event.call_count == 1
```

### conftest.py (共通fixture)

```python
import pytest
from unittest.mock import MagicMock
from v2.domain.ports import ConfigSource, FileStorage, DocumentAnalyzer, CalendarService, TaskService, Notifier

@pytest.fixture
def mock_config():
    mock = MagicMock(spec=ConfigSource)
    mock.load_profiles.return_value = {
        "CHILD1": Profile(id="CHILD1", name="太郎", grade="小3", keywords="", calendar_id="cal1")
    }
    mock.load_rules.return_value = []
    return mock

@pytest.fixture
def mock_storage():
    return MagicMock(spec=FileStorage)

# ... 他のモックも同様
```

---

## 実装フェーズ

### Phase 1: ドメイン基盤 ✅ (今回実装)

| ファイル | 内容 |
|---------|------|
| `v2/domain/models.py` | 全dataclass定義 |
| `v2/domain/errors.py` | 例外クラス |
| `v2/domain/ports.py` | 全Protocol定義 |
| `tests/unit/test_models.py` | モデルのテスト |
| `pyproject.toml` | pytest追加 |

**完了条件**: `pytest tests/unit/test_models.py` が全てpass

### Phase 2: ビジネスロジック ✅ (今回実装)

| ファイル | 内容 |
|---------|------|
| `tests/conftest.py` | 共通モックfixture |
| `tests/unit/test_action_dispatcher.py` | テスト先行 |
| `v2/services/action_dispatcher.py` | 実装 |
| `tests/unit/test_orchestrator.py` | テスト先行 |
| `v2/services/orchestrator.py` | 実装 |

**完了条件**: `pytest tests/` が全てpass（外部API不要）

### Phase 3: アダプタ層（次回以降）

- `v2/adapters/credentials.py` - 認証シングルトン
- `v2/adapters/google_drive.py` - Drive実装
- `v2/adapters/google_sheets.py` - Sheets実装
- `v2/adapters/gemini.py` - Gemini実装
- `v2/adapters/todoist.py` - Todoist実装
- `v2/adapters/slack.py` - Slack実装
- `v2/adapters/google_calendar.py` - Calendar実装

### Phase 4: エントリポイントと統合（次回以降）

- `v2/entrypoints/factory.py` - DI組み立て
- `v2/entrypoints/cli.py` - CLI実行
- `v2/entrypoints/cloud_function.py` - Cloud Functions
- `tests/integration/` - 結合テスト
- `tests/contract/` - LLM出力契約テスト

---

## 設計判断の根拠

### ABC vs Protocol
✅ **ABC採用**
- 実装漏れをインスタンス化時に即座に検出（Protocolは使用時まで検出されない）
- 継承関係が明示的
- School Agent v2は全て新規実装のアダプタなので、Protocolの利点（既存クラスをそのまま使える）が活かせない
- テストの書き方はProtocolと同じ（`MagicMock(spec=ABC)`）

### frozen dataclass vs Pydantic
✅ **frozen dataclass採用**
- 標準ライブラリのみで完結
- 不変性を型レベルで保証
- `__eq__` と `__hash__` が自動生成されテスト比較が容易
- Pydanticはバリデーションロジックが必要な場合に有用だが、今回のドメインモデルはシンプルなデータ構造のみ

### Constructor Injection vs Singleton
✅ **Constructor Injection採用**
- テスト時にモック差し替えが容易
- 依存関係が明示的
- factory.pyで本番環境の組み立てを一元管理

### logging vs print
✅ **logging採用**
- Cloud Loggingとの統合が容易
- テストで `caplog` fixtureで検証可能
- ログレベルの制御が可能

---

## LLMとの協調開発

このアーキテクチャはLLMと対話しながら開発することを想定しています。

### 開発サイクル例

```
User: "v2/adapters/todoist.py を実装してください"
  ↓
LLM: [コード生成]
  ↓
User: "pytest tests/unit/test_adapters/test_todoist.py を実行してください"
  ↓
LLM: [テスト実行、エラー確認、修正]
  ↓
User: "通知先をSlackからLINEに変更してください"
  ↓
LLM: "v2/adapters/line_notify.py を作成し、Notifier Protocolを実装します"
```

### LLM対話のポイント
- **テストファースト**: テストが通ることを会話のゴールに設定
- **小さい単位**: 1ファイルずつ実装→テスト→修正のサイクル
- **Protocol駆動**: 「このProtocolを満たす実装を書いて」と指示するだけ
- **外部API不要**: Phase 1-2は外部APIなしでテスト可能

---

## まとめ

School Agent v2は、テスト可能性と拡張容易性を最優先した設計です。Hexagonal Architectureにより、ビジネスロジックは外部APIから完全に独立し、LLMとの対話でテストベースの開発が可能になります。

**Phase 1-2の実装後、外部API実装なしでビジネスロジック全体のテストが通る状態**になります。
