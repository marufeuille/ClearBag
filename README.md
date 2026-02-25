# ClearBag

学校配布物（プリント・PDF）をAIが自動解析し、カレンダーとタスクに一括登録するB2C SaaSアプリ。

## 概要

保護者がスマホでお便りを撮影・アップロードするだけで、Gemini 2.5 Pro が内容を解析し、予定・タスクを自動抽出。PWAとして動作し、ホーム画面に追加してネイティブアプリのように使える。

## 機能

| 機能 | 説明 |
|---|---|
| **ドキュメントアップロード** | PDF・画像（JPG/PNG/WebP/HEIC）をアップロード、または写真撮影 |
| **AI解析** | Gemini 2.5 Pro が予定・タスク・サマリーを自動抽出 |
| **カレンダー表示** | 抽出された予定を日付順で一覧 |
| **タスク管理** | 期限付きタスクを一覧・完了チェック |
| **家族プロファイル** | 子どもごとのプロファイルで解析精度を向上 |
| **iCal連携** | カレンダーアプリへの購読URLを発行 |
| **PWA対応** | ホーム画面追加・オフラインUI |
| **無料プラン** | 月5枚まで無料解析 |

## アーキテクチャ

```
[PWA (Next.js)]  →  [FastAPI on Cloud Run Service]  →  [Cloud Tasks]
      │                        │                              │
  Firebase Hosting         Firebase Auth              [Worker Endpoint]
                           Firestore                         │
                           GCS (uploads)             [Vertex AI Gemini]
```

- **フロントエンド**: Next.js 15 (App Router) / Tailwind CSS / Firebase Hosting
- **バックエンド**: FastAPI / Cloud Run Service
- **非同期処理**: Cloud Tasks → Cloud Run Worker（ローカルは BackgroundTasks）
- **認証**: Firebase Authentication (Google Sign-in)
- **DB**: Firestore（ユーザー・ドキュメント・イベント・タスク）
- **ストレージ**: GCS（アップロードファイル）
- **AI**: Vertex AI Gemini 2.5 Pro
- **インフラ**: Terraform（dev / prod 環境分離）
- **設計**: Hexagonal Architecture (Ports & Adapters)

## ディレクトリ構成

```
.
├── v2/                        # バックエンド本体
│   ├── domain/
│   │   ├── models.py          # ドメインモデル（DocumentRecord, EventData 等）
│   │   ├── ports.py           # ABCポート定義
│   │   └── errors.py
│   ├── services/
│   │   └── document_processor.py  # AI解析コアロジック
│   ├── adapters/
│   │   ├── firestore_repository.py # Firestore実装
│   │   ├── cloud_storage.py        # GCS実装
│   │   ├── cloud_tasks_queue.py    # Cloud Tasks実装
│   │   ├── gemini.py               # Vertex AI Gemini実装（tenacityリトライ付き）
│   │   ├── ical_renderer.py        # iCal生成
│   │   ├── email_notifier.py       # SendGrid通知
│   │   └── webpush_notifier.py     # WebPush通知
│   ├── entrypoints/
│   │   ├── api/
│   │   │   ├── app.py             # FastAPIアプリ定義
│   │   │   ├── deps.py            # DI・認証（Firebase Auth検証）
│   │   │   └── routes/            # APIルート（documents/events/tasks/profiles/settings/ical）
│   │   ├── worker.py              # Cloud Tasksワーカー（解析実行）
│   │   └── cli.py                 # バッチCLI（Cloud Run Jobs用）
│   ├── config.py
│   └── logging_config.py
├── frontend/                  # PWAフロントエンド
│   ├── src/
│   │   ├── app/               # Next.js App Router ページ
│   │   │   ├── page.tsx       # ランディング（ログイン）
│   │   │   ├── dashboard/     # ドキュメント一覧・アップロード
│   │   │   ├── calendar/      # カレンダー
│   │   │   ├── tasks/         # タスク
│   │   │   ├── profiles/      # 家族プロファイル管理
│   │   │   └── settings/      # 設定・iCal URL
│   │   ├── components/        # 共通コンポーネント
│   │   │   ├── NavBar.tsx     # ヘッダー＋ボトムナビ
│   │   │   ├── AuthGuard.tsx  # 認証ガード
│   │   │   ├── UploadArea.tsx # ドラッグ&ドロップ・カメラ撮影
│   │   │   └── DocumentList.tsx
│   │   ├── hooks/
│   │   │   └── useAuth.ts     # Firebase Auth フック
│   │   └── lib/
│   │       ├── api.ts         # バックエンドAPIクライアント
│   │       └── firebase.ts    # Firebase初期化
│   └── public/
│       └── manifest.json      # PWAマニフェスト
├── terraform/
│   ├── environments/
│   │   ├── dev/               # dev環境（Firestore/GCS/CloudTasks/CloudRun/Scheduler等）
│   │   └── prod/
│   └── modules/               # 共通モジュール
├── tests/
│   ├── unit/
│   └── integration/
├── docker-compose.yml         # ローカルエミュレーター（Firestore + fake-gcs）
├── Makefile                   # 開発コマンド
├── Dockerfile                 # API/Workerコンテナ（uvマルチステージビルド）
├── .env.local.example         # バックエンド環境変数テンプレート
└── .github/workflows/         # CI/CD
```

## ローカル開発

### 前提条件

- Docker Desktop
- uv（`brew install uv`）
- Node.js 20+
- Firebase プロジェクト（Google Sign-in 有効化済み）
- GCP Application Default Credentials（`gcloud auth application-default login`）

### セットアップ

```bash
# 1. 依存関係インストール
uv sync

# 2. 環境変数ファイルを作成
cp .env.local.example .env.local
cp frontend/.env.local.example frontend/.env.local
# → 各ファイルを編集して値を設定
```

#### `.env.local` の主な設定項目

```env
LOCAL_MODE=true                          # BackgroundTasksで解析実行（Cloud Tasks不要）
DISABLE_RATE_LIMIT=true                  # 月間5枚制限をスキップ
PROJECT_ID=your-gcp-project-id           # Vertex AI用GCPプロジェクト
FIREBASE_PROJECT_ID=your-firebase-project-id  # Firebase認証プロジェクト（GCPと異なる場合）
FIRESTORE_EMULATOR_HOST=localhost:8089   # Firestoreエミュレーター
STORAGE_EMULATOR_HOST=http://localhost:4443  # GCSエミュレーター
GCS_BUCKET_NAME=clearbag-local
VERTEX_AI_LOCATION=asia-northeast1
GEMINI_MODEL=gemini-2.5-pro
ALLOWED_EMAILS=you@gmail.com             # ログイン制限（未設定で全員許可）
```

#### `frontend/.env.local` の主な設定項目

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=...         # Firebase コンソール → プロジェクト設定 → ウェブアプリ
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
# 他 Firebase 設定値
```

### 起動

```bash
# Terminal 1: Firestoreエミュレーター + fake-gcs起動
make dev-infra

# Terminal 2: FastAPIバックエンド（port 8000、ホットリロード）
make dev-backend

# Terminal 3: Next.jsフロントエンド（port 3000）
make dev-frontend
```

| URL | 用途 |
|---|---|
| http://localhost:3000 | フロントエンド（PWA） |
| http://localhost:8000 | バックエンドAPI |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8089 | Firestoreエミュレーター |
| http://localhost:4443 | GCSエミュレーター（fake-gcs） |

### Makefile コマンド一覧

```bash
make dev-infra     # エミュレーター起動
make dev-backend   # バックエンド起動
make dev-frontend  # フロントエンド起動
make stop          # エミュレーター停止
make test          # Pythonテスト実行
make lint          # リント実行
```

## API エンドポイント

| Method | Path | 説明 |
|---|---|---|
| `POST` | `/api/documents/upload` | ファイルアップロード（202 Accepted） |
| `GET` | `/api/documents` | ドキュメント一覧 |
| `GET` | `/api/documents/{id}` | ドキュメント詳細 |
| `DELETE` | `/api/documents/{id}` | ドキュメント削除 |
| `GET` | `/api/events` | イベント一覧（日付範囲フィルター） |
| `GET` | `/api/tasks` | タスク一覧 |
| `PATCH` | `/api/tasks/{id}` | タスク完了状態更新 |
| `GET` | `/api/profiles` | プロファイル一覧 |
| `POST` | `/api/profiles` | プロファイル作成 |
| `PUT` | `/api/profiles/{id}` | プロファイル更新 |
| `DELETE` | `/api/profiles/{id}` | プロファイル削除 |
| `GET` | `/api/settings` | ユーザー設定取得 |
| `PATCH` | `/api/settings` | ユーザー設定更新 |
| `GET` | `/api/ical/{token}` | iCalフィード（認証不要） |
| `POST` | `/worker/analyze` | 解析ジョブ実行（Cloud Tasksから呼び出し） |
| `GET` | `/health` | ヘルスチェック |

## CI/CD

| トリガー | ワークフロー | 内容 |
|---|---|---|
| PR | `ci.yml` | Lint (ruff) + テスト |
| `main` push | `cd-dev.yml` | Lint → Docker ビルド → Terraform Apply (dev) → Firebase Hosting deploy |
| `v*` タグ | `cd-prod-build.yml` | Docker ビルド & `latest-prod` タグ付与 |
| `v*` タグ | `cd-prod-terraform.yml` | Terraform Apply (prod) |

GCP 認証は Workload Identity Federation (OIDC) を使用（静的キー不使用）。

## テスト

```bash
# ユニットテスト
uv run pytest tests/unit -v

# カバレッジ付き
uv run pytest tests/ --cov=v2 --cov-report=term-missing
```

## デプロイ

### 初回（dev環境）

```bash
# 1. Terraformでインフラ構築
cd terraform/environments/dev
terraform init
terraform apply

# 2. Secret Managerにシークレットを登録
gcloud secrets versions add sendgrid-api-key --data-file=- <<< "your-key"

# 3. GitHub Secretsを設定
#    NEXT_PUBLIC_FIREBASE_API_KEY, NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN, ...

# 4. main ブランチにpush → CI/CDが自動デプロイ
```

### リリース（prod環境）

```bash
git tag v1.0.0
git push origin v1.0.0
# → prod Docker ビルド → Terraform Apply (prod) が自動実行
```

## セキュリティ

- Firebase Authentication による JWT 検証（全 API エンドポイント）
- `ALLOWED_EMAILS` 環境変数でログイン可能アカウントを制限（dev環境推奨）
- Workload Identity Federation（サービスアカウントキー不使用）
- Cloud Tasks Worker は OIDC トークンで保護

## ドキュメント

- [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md) - アーキテクチャ詳細
- [SPECIFICATION.md](SPECIFICATION.md) - システム仕様書
- [docs/plan/commercialization-mvp.md](docs/plan/commercialization-mvp.md) - B2C化実装プラン
- [docs/review/nonfunctional-analysis-2026-02-23.md](docs/review/nonfunctional-analysis-2026-02-23.md) - 非機能要件分析

## ライセンス

[MIT](LICENSE)
