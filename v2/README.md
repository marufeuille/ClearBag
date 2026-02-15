# School Agent v2

学校配布物管理アプリのHexagonal Architectureリファクタリング版

## Phase 1-4 完了 ✅

### 実装内容

- ✅ **Phase 1-2**: ドメインモデル、Ports（ABC）、ビジネスロジック、ユニットテスト（31テスト、100%カバレッジ）
- ✅ **Phase 3**: 全アダプタ実装（Google Sheets, Drive, Calendar, Gemini, Slack, Todoist）
- ✅ **Phase 4**: エントリーポイント（Factory, CLI, Cloud Functions）、統合テスト

### ディレクトリ構造

```
v2/
├── domain/          # ドメインモデル・ポート定義
│   ├── models.py    # 8つのdataclass（Profile, Rule, EventData等）
│   ├── errors.py    # ドメイン固有の例外
│   └── ports.py     # 6つのABC（ConfigSource, FileStorage等）
├── services/        # ビジネスロジック
│   ├── orchestrator.py       # メインワークフロー
│   └── action_dispatcher.py  # 解析結果→アクション振り分け
├── adapters/        # 外部サービス実装
│   ├── credentials.py        # Google認証
│   ├── google_sheets.py      # ConfigSource実装
│   ├── google_drive.py       # FileStorage実装
│   ├── google_calendar.py    # CalendarService実装
│   ├── gemini.py             # DocumentAnalyzer実装（Gemini 2.5 Pro）
│   ├── todoist.py            # TaskService実装
│   └── slack.py              # Notifier実装
├── entrypoints/     # エントリーポイント
│   ├── factory.py            # DI組み立て（Null Object Pattern含む）
│   ├── cli.py                # CLI実行
│   └── cloud_function.py     # Cloud Functions実行
└── config.py        # 環境変数からの設定読み込み

tests/
├── conftest.py        # 共通fixture（モックとサンプルデータ）
└── unit/
    ├── test_models.py
    ├── test_action_dispatcher.py
    └── test_orchestrator.py

# ルートディレクトリ
test_adapters.py     # アダプタ個別動作確認
test_v2_e2e.py       # End-to-End統合テスト
main_v2.py           # Cloud Functionsデプロイ用
```

## セットアップ

### 1. 環境変数設定

`.env` ファイルを作成:

```bash
# 必須
PROJECT_ID=your-gcp-project-id
SPREADSHEET_ID=your-google-sheets-id
INBOX_FOLDER_ID=your-drive-inbox-folder-id
ARCHIVE_FOLDER_ID=your-drive-archive-folder-id

# オプショナル（未設定の場合はスキップ）
TODOIST_API_TOKEN=your-todoist-token
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_ID=C01234567

# デフォルト値あり
VERTEX_AI_LOCATION=us-central1  # デフォルト: us-central1
GEMINI_MODEL=gemini-2.5-pro     # デフォルト: gemini-2.5-pro
```

### 2. Google認証

Service Accountの認証情報を配置:

```bash
# 方法1: 環境変数で指定
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 方法2: デフォルトパスに配置
cp service-account-key.json ~/.config/gcloud/application_default_credentials.json
```

### 3. 依存パッケージインストール

```bash
uv sync
```

## 実行方法

### CLI実行

```bash
# 基本実行
python -m v2.entrypoints.cli

# ログレベル変更
LOG_LEVEL=DEBUG python -m v2.entrypoints.cli
```

### 統合テスト（End-to-End）

```bash
# Inboxにテスト用ファイルを配置してから実行
python test_v2_e2e.py
```

### 個別アダプタテスト

```bash
# 各アダプタの動作確認
python test_adapters.py
```

## ユニットテスト

```bash
# 全テスト実行
pytest tests/ -v

# カバレッジ付き
pytest tests/ --cov=v2 --cov-report=html

# 特定テストのみ
pytest tests/unit/test_orchestrator.py -v
```

**現在のカバレッジ: 100%（31テスト全パス）**

## Cloud Functionsデプロイ

### デプロイコマンド

```bash
gcloud functions deploy school-agent-v2 \
  --gen2 \
  --runtime=python313 \
  --region=us-central1 \
  --source=. \
  --entry-point=school_agent_http \
  --trigger-http \
  --allow-unauthenticated \
  --timeout=540s \
  --memory=512Mi \
  --set-env-vars PROJECT_ID=xxx,SPREADSHEET_ID=xxx,INBOX_FOLDER_ID=xxx,ARCHIVE_FOLDER_ID=xxx
```

### Cloud Schedulerで定期実行

```bash
# 毎日9時に実行
gcloud scheduler jobs create http school-agent-daily \
  --schedule="0 9 * * *" \
  --uri="https://us-central1-xxx.cloudfunctions.net/school-agent-v2" \
  --http-method=POST \
  --time-zone="Asia/Tokyo"
```

## 設計原則

### 1. Hexagonal Architecture
- **Domain層**: ビジネスロジックのみ。外部依存なし。
- **Ports**: ABCで定義（Protocol不使用）。型安全性を確保。
- **Adapters**: 外部サービス実装。ポートに準拠。
- **Entrypoints**: 依存性を組み立ててドメインを起動。

### 2. 重要な設計判断

1. **ABC > Protocol**: 実装漏れをインスタンス化時に即座に検出。全て新規実装なのでABCが適切
2. **frozen dataclass > Pydantic**: 標準ライブラリのみ。不変性保証。テスト比較容易
3. **Constructor Injection**: テスト時にモック差し替えが容易
4. **logging > print**: テストで`caplog` fixture検証可能
5. **Null Object Pattern**: オプショナルサービス（Todoist/Slack）の優雅な処理

### 3. テスタビリティ
- モックを使った完全なユニットテスト
- 実際のAPIを使った統合テスト
- 100%コードカバレッジ達成

### 4. 拡張性
- 新しい通知先追加: `Notifier` ABCを実装するだけ
- 新しいストレージ: `FileStorage` ABCを実装するだけ
- 新しいLLM: `DocumentAnalyzer` ABCを実装するだけ

## トラブルシューティング

### カレンダーイベントが見つからない

Service Accountのカレンダーに登録されている可能性があります。
Google Sheetsの `calendar_id` カラムが正しく設定されているか確認してください。

### Todoist/Slack通知が送信されない

トークンが設定されていない場合、Null Objectパターンで処理がスキップされます。
ログに以下のメッセージが出力されます:

```
WARNING: TODOIST_API_TOKEN not set, tasks will not be created
WARNING: Slack tokens not set, notifications will not be sent
```

必要に応じて `.env` にトークンを追加してください。

### Gemini解析エラー

- `PROJECT_ID` が正しいか確認
- Service Accountに Vertex AI User ロールが付与されているか確認
- リージョン（`VERTEX_AI_LOCATION`）が正しいか確認

## 既存コード（src/）との違い

| 項目 | src/ (v1) | v2/ |
|------|-----------|-----|
| アーキテクチャ | モノリシック | Hexagonal |
| テスト | 困難（外部API直接依存） | 容易（DI + モック） |
| カバレッジ | なし | 100% |
| エラーハンドリング | 部分的 | 全パイプライン |
| 拡張性 | 低い | 高い（ポート追加のみ） |
| ログ | print文 | logging モジュール |
| 設定管理 | グローバル変数 | AppConfig dataclass |

## 次のステップ

1. ✅ Phase 1-2: ドメイン・サービス層実装（完了）
2. ✅ Phase 3: 全アダプタ実装（完了）
3. ✅ Phase 4: エントリーポイント・統合（完了）
4. 🔄 Phase 5: 本番環境デプロイ
5. 📝 Phase 6: src/ からの完全移行検討

## 詳細ドキュメント

- [ARCHITECTURE_V2.md](../ARCHITECTURE_V2.md) - 設計詳細
- [SPECIFICATION.md](../SPECIFICATION.md) - システム仕様
