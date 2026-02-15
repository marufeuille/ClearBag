# Phase 3 実装ガイド - Adapter層の実装

Phase 1-2でドメインモデルとビジネスロジックが完成しました。
Phase 3では各外部サービスとの連携を実装します。

## 実装対象

```
v2/adapters/
├── __init__.py
├── credentials.py       # Google API認証の一元管理
├── google_drive.py      # FileStorage 実装
├── google_sheets.py     # ConfigSource 実装
├── gemini.py            # DocumentAnalyzer 実装
├── todoist.py           # TaskService 実装
├── slack.py             # Notifier 実装
└── google_calendar.py   # CalendarService 実装
```

## 実装パターン（ABC継承）

全てのアダプタは `v2/domain/ports.py` で定義されたABCを継承します。

### 例: FileStorage実装

```python
# v2/adapters/google_drive.py
from v2.domain.ports import FileStorage
from v2.domain.models import FileInfo

class GoogleDriveAdapter(FileStorage):  # ← ABCを継承
    """
    FileStorage ABCの実装。
    実装漏れがあるとインスタンス化時にエラーになる。
    """

    def __init__(self, credentials, inbox_folder_id: str, archive_folder_id: str):
        self._service = build('drive', 'v3', credentials=credentials)
        self._inbox_id = inbox_folder_id
        self._archive_id = archive_folder_id

    def list_inbox_files(self) -> list[FileInfo]:
        """FileStorage.list_inbox_files の実装"""
        results = self._service.files().list(
            q=f"'{self._inbox_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, webViewLink)",
        ).execute()

        items = results.get('files', [])
        return [
            FileInfo(
                id=item['id'],
                name=item['name'],
                mime_type=item['mimeType'],
                web_view_link=item.get('webViewLink', ''),
            )
            for item in items
        ]

    def download(self, file_id: str) -> bytes:
        """FileStorage.download の実装"""
        request = self._service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return fh.getvalue()

    def archive(self, file_id: str, new_name: str) -> None:
        """FileStorage.archive の実装"""
        file = self._service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents', []))

        self._service.files().update(
            fileId=file_id,
            addParents=self._archive_id,
            removeParents=previous_parents,
            body={'name': new_name},
            fields='id, parents'
        ).execute()
```

## ABCのメリット（Phase 3で実感できる）

### 1. 実装漏れを即座に検出

```python
class IncompleteAdapter(FileStorage):
    def list_inbox_files(self) -> list[FileInfo]:
        return []

    # download と archive を忘れた！

adapter = IncompleteAdapter()  # ❌ TypeError: Can't instantiate abstract class
```

### 2. IDEの補完が効く

- ABCを継承すると、IDEが実装すべきメソッドを提示してくれる
- PyCharm, VSCode等で「Implement methods」が使える

### 3. mypyで型チェック

```bash
uv run mypy v2/adapters/google_drive.py
```

実装漏れがあれば即座にエラー。

## 既存コード（src/）からの移植

既存の `src/` 配下のコードを参考にしてください：

| 既存ファイル | 新ファイル | 移植内容 |
|-------------|-----------|---------|
| `src/config.py` | `v2/adapters/credentials.py` | `get_credentials()` 関数 |
| `src/config.py` | `v2/adapters/google_sheets.py` | `load_config_from_sheet()` |
| `src/drive_utils.py` | `v2/adapters/google_drive.py` | 全関数 |
| `src/gemini_client.py` | `v2/adapters/gemini.py` | `analyze_document()` |
| `src/calendar_client.py` | `v2/adapters/google_calendar.py` | `add_calendar_event()` |
| `src/todoist_client.py` | `v2/adapters/todoist.py` | `create_todoist_task()` |
| `src/slack_client.py` | `v2/adapters/slack.py` | `send_slack_file_notification()` |

## LLMへの指示例

```
"v2/adapters/google_drive.py を実装してください。

要件:
- FileStorage ABCを継承
- 既存の src/drive_utils.py のロジックを移植
- コンストラクタでcredentials, inbox_folder_id, archive_folder_idを受け取る
- list_inbox_files, download, archive の3つのメソッドを実装
- FileInfo dataclassを返すように変換"
```

## テストの書き方

各アダプタのユニットテストは不要です（外部API呼び出しのテストは困難）。
代わりに：

1. **Phase 2のテストで既にカバー済み**: モックで動作確認
2. **Phase 4で統合テスト**: 実際のアダプタを使った結合テスト

## 次のステップ

Phase 3完了後:
- Phase 4: factory.py でDI組み立て
- Phase 4: CLI / Cloud Functions エントリポイント
- Phase 4: 統合テスト
