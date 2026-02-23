# ClearBag

学校プリントを自動処理するAIエージェント。Google Drive の Inbox フォルダを監視し、Gemini 2.5 Pro で内容を解析してカレンダー・Todoist・Slack に自動連携する。

## 機能

- **自動スキャン**: 特定の Google Drive フォルダ (`Inbox`) を監視
- **AI解析**: Gemini 2.5 Pro で文書の内容・日付・アクションを理解
- **カレンダー連携**: 家族メンバーごとの Google カレンダーに予定を追加
- **タスク管理**: アクションが必要な項目を Todoist に登録
- **通知**: 処理結果の要約を Slack に送信
- **アーカイブ**: ファイルを `YYYYMMDD_タイトル` にリネームして `Archive` フォルダに移動

## アーキテクチャ

- **言語**: Python 3.13
- **設計**: Hexagonal Architecture (Ports & Adapters)
- **AI**: Google Vertex AI (Gemini 2.5 Pro)
- **ストレージ**: Google Drive
- **設定管理**: Google Sheets
- **連携**: Google Calendar, Todoist, Slack
- **実行基盤**: Cloud Run Jobs（Cloud Scheduler で毎日 9:00 / 17:00 JST）
- **インフラ**: Terraform（`dev` / `prod` 環境分離）

## ディレクトリ構成

```
.
├── v2/                    # アプリケーション本体（Hexagonal Architecture）
│   ├── domain/           # ドメインモデル・ポート定義
│   │   ├── models.py     # dataclass（Profile, Rule, EventData 等）
│   │   ├── errors.py     # ドメイン固有の例外
│   │   └── ports.py      # ABC ポート（ConfigSource, FileStorage 等）
│   ├── services/         # ビジネスロジック
│   │   ├── orchestrator.py       # メインワークフロー
│   │   └── action_dispatcher.py  # 解析結果→アクション振り分け
│   ├── adapters/         # 外部サービス実装
│   │   ├── credentials.py
│   │   ├── google_sheets.py
│   │   ├── google_drive.py
│   │   ├── google_calendar.py
│   │   ├── gemini.py
│   │   ├── todoist.py
│   │   └── slack.py
│   ├── entrypoints/      # エントリーポイント
│   │   ├── factory.py    # DI 組み立て（Null Object Pattern 含む）
│   │   └── cli.py        # CLI 実行
│   └── config.py         # 環境変数からの設定読み込み
├── terraform/             # インフラ定義
│   ├── environments/
│   │   ├── dev/          # dev 環境
│   │   └── prod/         # prod 環境
│   └── modules/          # 共通モジュール
│       ├── artifact_registry/
│       ├── cloud_run_job/
│       ├── cloud_scheduler/
│       ├── secret_manager/
│       └── workload_identity/
├── .github/workflows/     # CI/CD
│   ├── ci.yml            # Lint + Test（PR 時）
│   ├── cd-dev.yml        # dev デプロイ（main push）
│   ├── cd-prod-build.yml # prod Docker ビルド（v* タグ）
│   └── cd-prod-terraform.yml # prod Terraform Apply（v* タグ）
├── tests/
│   ├── unit/             # ユニットテスト（37 tests）
│   ├── integration/      # 統合テスト
│   ├── e2e/              # End-to-End テスト
│   └── manual/           # 手動実行用
├── Dockerfile
├── build_push.sh          # ローカルから Docker ビルド & push
├── pyproject.toml
├── ARCHITECTURE_V2.md
└── SPECIFICATION.md
```

## セットアップ

### 前提条件

- Google Cloud Project（Drive / Sheets / Calendar / Vertex AI API 有効化）
- 適切な権限を持つサービスアカウント
- Todoist アカウント & API トークン（オプション）
- Slack ワークスペース & Bot トークン（オプション）

### インストール

```bash
git clone <repository-url>
cd ClearBag
uv sync
```

### 環境変数

ルートディレクトリに `.env` ファイルを作成:

```env
# 必須
PROJECT_ID=your-google-cloud-project-id
SPREADSHEET_ID=your-config-sheet-id
INBOX_FOLDER_ID=your-inbox-drive-folder-id
ARCHIVE_FOLDER_ID=your-archive-drive-folder-id

# オプション（未設定の場合はスキップ）
TODOIST_API_TOKEN=your-todoist-token
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_ID=your-slack-channel-id

# デフォルト値あり
VERTEX_AI_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-pro
```

認証情報:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

## 使用方法

### CLI 実行

```bash
uv run python -m v2.entrypoints.cli

# デバッグ
LOG_LEVEL=DEBUG uv run python -m v2.entrypoints.cli
```

### Cloud Run Jobs（本番）

Terraform でデプロイ済み。Cloud Scheduler が毎日 9:00 / 17:00 JST に自動実行する。

## CI/CD

| トリガー | ワークフロー | 内容 |
|----------|-------------|------|
| PR | `ci.yml` | Lint (ruff) + Unit/Integration テスト |
| `main` push | `cd-dev.yml` | Lint + テスト → Docker ビルド → Terraform Apply (dev) |
| `v*` タグ | `cd-prod-build.yml` | Docker ビルド & `latest-prod` タグ付与 |
| `v*` タグ | `cd-prod-terraform.yml` | Terraform Apply (prod) |

GCP 認証は Workload Identity Federation (OIDC) を使用。

## テスト

```bash
# ユニットテスト
uv run pytest tests/unit -v

# カバレッジ付き
uv run pytest tests/unit tests/integration -m "not manual" --cov=v2 --cov-report=term-missing
```

現在のテストカバレッジ: **100% (37 unit tests)**

## 設計原則

**Hexagonal Architecture**:

- **Domain 層**: ビジネスロジックのみ。外部依存なし。
- **Ports**: ABC で定義。型安全性を確保。
- **Adapters**: 外部サービス実装。ポートに準拠。
- **Entrypoints**: 依存性を組み立ててドメインを起動。

主な設計判断: ABC > Protocol（実装漏れをインスタンス化時に検出）、frozen dataclass（不変性保証）、Null Object Pattern（オプショナルサービスの優雅な処理）。

## ドキュメント

- [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md) - 設計詳細
- [SPECIFICATION.md](SPECIFICATION.md) - システム仕様書
- [docs/](docs/) - 各種計画・レビュードキュメント

## ライセンス

[MIT](LICENSE)
