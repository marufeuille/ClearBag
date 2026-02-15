# School Agent

学校のプリントや書類の処理を自動化するAIエージェントです。Google Driveからファイルを読み込み、Google Geminiを使って内容・文脈・日付を解析し、自動的にGoogleカレンダーへの予定登録、Todoistへのタスク追加、Slackへの通知を行います。

## 機能

- **自動スキャン**: 特定のGoogle Driveフォルダ (`Inbox`) を監視します。
- **AI解析**: Gemini 1.5 Pro を使用して、文書の内容を理解します。
- **カレンダー連携**: 家族メンバーごとに指定されたGoogleカレンダーに予定を追加します。
- **タスク管理**: アクションが必要な項目（例：「提出」「持ち物」）をTodoistに登録します。
- **通知**: 処理結果の要約をSlackに送信します。
- **アーカイブ**: ファイルを検索しやすい名前 (`YYYYMMDD_タイトル`) にリネームし、`Archive` フォルダに移動します。

## アーキテクチャ

- **言語**: Python
- **AI**: Google Vertex AI (Gemini 1.5 Pro)
- **ストレージ**: Google Drive
- **設定管理**: Google Sheets
- **連携**: Google Calendar, Todoist, Slack

## セットアップ

### 1. 前提条件

- Google Cloud Project (以下のAPIを有効化):
    - Google Drive API
    - Google Sheets API
    - Google Calendar API
    - Vertex AI API
- 適切な権限を持つサービスアカウント
- Todoist アカウント & APIトークン
- Slack ワークスペース & Botトークン

### 2. インストール

本プロジェクトはパッケージ管理に [uv](https://github.com/astral-sh/uv) を使用しています。

```bash
git clone <repository-url>
cd school_ai_app
uv sync
```

### 3. 設定

1.  **Google Sheets**: `Profiles` と `Rules` タブを持つ設定用シートを作成します（詳細は `SPECIFICATION.md` 参照）。
2.  **環境変数**: ルートディレクトリに `.env` ファイルを作成します:

```env
PROJECT_ID=your-google-cloud-project-id
SPREADSHEET_ID=your-config-sheet-id
INBOX_FOLDER_ID=your-inbox-drive-folder-id
ARCHIVE_FOLDER_ID=your-archive-drive-folder-id
TODOIST_API_TOKEN=your-todoist-token
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_ID=your-slack-channel-id
```

3.  **認証情報**: `service_account.json` をルートディレクトリに配置します。

### 4. 使用方法

エージェントスクリプトを実行します:

```bash
uv run src/main.py
```

## ディレクトリ構成

```
.
├── src/
│   ├── main.py           # エントリーポイント
│   ├── config.py         # 設定読み込み
│   ├── drive_utils.py    # Google Drive 操作
│   ├── gemini_client.py  # Vertex AI クライアント
│   ├── calendar_client.py# Google Calendar クライアント
│   ├── todoist_client.py # Todoist クライアント
│   └── slack_client.py   # Slack クライアント
├── .env                  # 環境変数 (git管理外)
├── requirements.txt      # Python依存ライブラリ
├── service_account.json  # Google認証情報 (git管理外)
└── SPECIFICATION.md      # システム仕様書
```

## ライセンス

[MIT](LICENSE)
