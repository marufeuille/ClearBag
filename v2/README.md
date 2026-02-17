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
├── unit/              # ユニットテスト
│   ├── test_models.py
│   ├── test_action_dispatcher.py
│   └── test_orchestrator.py
├── integration/       # 統合テスト（実際のAPIを使用）
│   └── test_adapters_manual.py
├── e2e/              # End-to-Endテスト
│   └── test_v2_full_pipeline.py
└── manual/           # 手動実行用テスト・ユーティリティ
    ├── adapters/     # アダプタ個別テスト
    │   ├── test_all_adapters.py
    │   ├── test_gemini.py
    │   ├── test_calendar_today.py
    │   └── test_calendar_with_profile.py
    └── utils/        # ユーティリティスクリプト
        ├── check_folders.py
        ├── upload_sample_to_inbox.py
        ├── debug_calendar.py
        └── verify_cloud.py

# ルートディレクトリ
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

### End-to-Endテスト

```bash
# 完全なパイプライン統合テスト
uv run python -m pytest tests/e2e/test_v2_full_pipeline.py -v

# または直接実行
uv run python tests/e2e/test_v2_full_pipeline.py
```

### 個別アダプタテスト

```bash
# 全アダプタの動作確認
uv run python tests/manual/adapters/test_all_adapters.py

# 個別テスト
uv run python tests/manual/adapters/test_gemini.py
uv run python tests/manual/adapters/test_calendar_today.py
```

### ユーティリティスクリプト

```bash
# Inbox/Archiveフォルダの確認
uv run python tests/manual/utils/check_folders.py

# sample.pdfをInboxにアップロード（※Service Account制限のため手動推奨）
uv run python tests/manual/utils/upload_sample_to_inbox.py
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

### セキュリティ設定

Cloud Functionsは**認証必須**で、CloudScheduler経由のアクセスのみを許可します:
- `--no-allow-unauthenticated`: allUsers権限を付与しない
- CloudSchedulerは`--oidc-service-account-email`でService Accountの認証トークンを使用
- 直接のHTTPアクセスは**403 Forbidden**で拒否されます

### デプロイコマンド

```bash
gcloud functions deploy school-agent-v2 \
  --gen2 \
  --runtime=python313 \
  --region=us-central1 \
  --source=. \
  --entry-point=school_agent_http \
  --trigger-http \
  --no-allow-unauthenticated \
  --service-account=SERVICE_ACCOUNT_EMAIL \
  --timeout=540s \
  --memory=512Mi \
  --set-env-vars PROJECT_ID=xxx,SPREADSHEET_ID=xxx,INBOX_FOLDER_ID=xxx,ARCHIVE_FOLDER_ID=xxx
```

### Cloud Schedulerで定期実行

```bash
# 毎日9時に実行（OIDC認証でService Account経由でアクセス）
gcloud scheduler jobs create http school-agent-daily \
  --schedule="0 9 * * *" \
  --uri="https://us-central1-xxx.cloudfunctions.net/school-agent-v2" \
  --http-method=POST \
  --time-zone="Asia/Tokyo" \
  --oidc-service-account-email=SERVICE_ACCOUNT_EMAIL
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

### Service Account の設定

**重要**: `SERVICE_ACCOUNT_EMAIL`の設定は**オプション**です。

デプロイスクリプトの動作:

1. **環境変数** `SERVICE_ACCOUNT_EMAIL` が設定されている場合:
   - 指定されたService Accountを使用してFunctionをデプロイ
   - CloudSchedulerも同じアカウントでOIDC認証

2. **service_account.json** が存在する場合:
   - ファイルからService Accountメールを抽出して使用

3. **どちらも未設定の場合** (CI/CD環境で推奨):
   - Cloud Functionsは自動的に**Compute Engine default service account**を使用
   - CloudSchedulerはデプロイ後にFunctionから使用中のアカウントを取得

**推奨設定:**

```bash
# ローカル開発: service_account.json を配置
cp /path/to/service-account-key.json service_account.json

# CI/CD環境: 設定不要（デフォルトのCompute Engine SAを使用）
# Workload Identity Federation経由で認証するだけでOK
```

### 既存デプロイから allUsers 権限を削除

既にデプロイ済みのFunctionから`allUsers`権限を削除する方法:

```bash
# 1. 現在のIAMポリシーを確認
gcloud functions get-iam-policy school-agent-v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID

# 2. allUsers権限を削除
gcloud functions remove-iam-policy-binding school-agent-v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --member="allUsers" \
  --role="roles/cloudfunctions.invoker"

# 3. 削除されたことを確認（allUsersが表示されないこと）
gcloud functions get-iam-policy school-agent-v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID
```

または、`deploy_v2.sh`を再実行すると自動的に修正されます:
```bash
./deploy_v2.sh
```

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
