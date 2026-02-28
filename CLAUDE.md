# CLAUDE.md — ClearBag プロジェクト行動指針

Claude Code がこのリポジトリで作業する際の行動規範・コマンドリファレンス・ワークフローを定義する。

---

## 1. プロジェクト概要

学校配布物（PDF・画像）を **Gemini 2.5 Pro** で AI 解析し、Google Calendar / Todoist / Slack に自動連携する **B2C SaaS アプリ**。

| レイヤー | 技術スタック |
|---|---|
| バックエンド | Python 3.13 / FastAPI / Cloud Run Service |
| フロントエンド | Next.js 15 (App Router) / Tailwind CSS / Firebase Hosting |
| 非同期処理 | Cloud Tasks → Cloud Run Worker |
| 認証・DB | Firebase Authentication / Firestore |
| ストレージ | GCS |
| AI | Vertex AI Gemini 2.5 Pro |
| インフラ | Terraform (dev / prod 分離) |
| 設計 | Hexagonal Architecture (Ports & Adapters) |
| パッケージ管理 | uv |

---

## 2. ディレクトリ構成（主要パス）

```
.
├── v2/                            # バックエンド本体
│   ├── domain/
│   │   ├── models.py              # ドメインモデル (frozen dataclass)
│   │   ├── ports.py               # ABC ポート定義
│   │   └── errors.py
│   ├── services/
│   │   └── document_processor.py  # AI 解析コアロジック
│   ├── adapters/                  # Ports 実装（Firestore / GCS / Gemini 等）
│   ├── entrypoints/
│   │   ├── api/
│   │   │   ├── app.py             # FastAPI アプリ定義
│   │   │   ├── deps.py            # DI・認証 (Firebase Auth 検証)
│   │   │   └── routes/            # APIルート
│   │   └── worker.py              # Cloud Tasks ワーカー
│   ├── config.py                  # frozen dataclass + from_env()
│   └── logging_config.py
├── frontend/                      # PWA フロントエンド
│   ├── src/
│   │   ├── app/                   # Next.js App Router ページ
│   │   ├── components/
│   │   ├── hooks/
│   │   └── lib/
│   └── e2e/                       # Playwright E2E テスト
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/                       # Firestore Emulator を使った API E2E
├── terraform/
│   ├── environments/{dev,prod}/
│   └── modules/
├── scripts/                       # 運用スクリプト・マイグレーション
├── docs/
│   ├── plan/                      # 設計計画
│   └── review/                    # レビュー履歴・非機能分析
├── Makefile
└── .github/workflows/             # CI/CD
```

---

## 3. 開発環境セットアップ

### 前提条件
- Docker Desktop
- `uv`（`brew install uv`）
- Node.js 20+
- GCP Application Default Credentials（`gcloud auth application-default login`）

### セットアップ手順

```bash
# 依存関係インストール
uv sync

# 環境変数ファイルを作成して設定
cp .env.local.example .env.local          # PROJECT_ID, VERTEX_AI_LOCATION 等を設定
cp frontend/.env.local.example frontend/.env.local  # Firebase 設定を記入
```

### 起動（ターミナル 3 つ）

```bash
make dev-infra     # Terminal 1: Firestore + GCS エミュレーター起動
make dev-backend   # Terminal 2: FastAPI (port 8000, ホットリロード)
make dev-frontend  # Terminal 3: Next.js (port 3000)
```

| URL | 用途 |
|---|---|
| http://localhost:3000 | フロントエンド (PWA) |
| http://localhost:8000 | バックエンド API |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8089 | Firestore エミュレーター |
| http://localhost:4443 | GCS エミュレーター |

---

## 4. よく使うコマンド

### Makefile ターゲット

```bash
make dev-infra     # Firestore + GCS エミュレーター起動
make dev-backend   # FastAPI バックエンド起動
make dev-frontend  # Next.js フロントエンド起動
make stop          # エミュレーター停止
make test          # Python テスト実行 (tests/ 全体)
make lint          # ruff check + format --check
```

### バックエンド（Python / uv）

```bash
uv run ruff check v2/ tests/              # lint チェック
uv run ruff check --fix v2/ tests/       # lint 自動修正
uv run ruff format v2/ tests/            # フォーマット適用
uv run pytest tests/unit/ tests/integration/ -m "not manual" -v  # ユニット+統合テスト
uv run pytest tests/unit/ tests/integration/ -v --cov=v2 --cov-report=term-missing  # カバレッジ付き
```

### フロントエンド（Node.js / npm）

```bash
cd frontend
npm run dev         # 開発サーバー起動 (port 3000)
npm run lint        # ESLint (next lint)
npm run build       # プロダクションビルド
npm run test:e2e    # Playwright E2E テスト（next dev を自動起動）
```

---

## 5. テストルール

### 5a. テスト駆動開発（TDD・柔軟）

- **すべての変更にはテストが伴うこと**（テストなしの実装コミットは避ける）
- テストファースト推奨だが、実装と並行してもよい
- ユニットテスト: `tests/unit/` に配置
- テストパターン: **Arrange-Act-Assert**、`TestClass` ベース、`conftest.py` の共通フィクスチャ活用
- モック: `MagicMock(spec=ABC)` を使用（型安全なモック）
- API テスト: `TestClient` + `dependency_overrides` で DI を置き換え

```python
# テスト例のパターン
class TestMyFeature:
    def test_happy_path(self, ...):
        # Arrange
        ...
        # Act
        response = client.post("/api/...")
        # Assert
        assert response.status_code == 200
```

### 5b. 要件検証スクリプト（変更前後の確認）

**コード変更時は、変更前後の挙動を検証可能なコードとして記録すること。**

- **推奨**: `tests/e2e/` に pytest E2E テストとして追加（CI 自動実行 + Firestore Emulator）
- **代替**: pytest が困難な場合は `scripts/verify_*.sh` 等のスクリプトでもよい
- dev 環境デプロイ後に実行し、要件が満たされていることを確認する

```bash
# バックエンド E2E テスト（Firestore Emulator 使用）
docker run -d -p 8080:8080 --name firestore-emulator \
  google/cloud-sdk:emulators \
  gcloud emulators firestore start --host-port=0.0.0.0:8080

FIRESTORE_EMULATOR_HOST=localhost:8080 uv run pytest tests/e2e/ -m e2e -v
```

### 5c. テストコマンドまとめ

| 対象 | コマンド |
|---|---|
| ユニット + 統合 | `uv run pytest tests/unit/ tests/integration/ -m "not manual" -v` |
| バックエンド E2E | `FIRESTORE_EMULATOR_HOST=localhost:8080 uv run pytest tests/e2e/ -m e2e -v` |
| フロントエンド E2E | `cd frontend && npm run test:e2e` |
| 全体 | `make test` |

---

## 6. コード変更 → PR → マージ → デプロイフロー

**特に指定がない場合、以下のステップを順に実行すること。**

### ステップ 1: ブランチ作成・実装

```bash
git checkout -b feat/your-feature-name
# ... 実装 ...
```

### ステップ 2: テスト実行（変更前後の比較確認）

```bash
make lint
uv run pytest tests/unit/ tests/integration/ -m "not manual" -v
# フロントエンドを変更した場合:
cd frontend && npm run test:e2e
```

### ステップ 3: コミット・プッシュ・PR 作成

```bash
git add <files>
git commit -m "feat: ..."
git push origin feat/your-feature-name
gh pr create --title "..." --body "..."
```

### ステップ 4: CI 監視

```bash
gh run list                    # 実行中のワークフロー確認
gh run watch <run-id>          # 特定の実行を監視
```

PR に対して以下の CI が自動実行される:

| ワークフロー | 内容 |
|---|---|
| `ci.yml` | ruff lint + pytest (unit/integration/e2e) + Firestore rules |
| `ci-frontend.yml` | Playwright E2E テスト |
| `tf-cmt-dev.yml` | Terraform plan コメント（terraform 変更時） |

### ステップ 5: CI 失敗時

```bash
gh run view <run-id> --log-failed    # 失敗ログを確認
# → 修正してコミット・プッシュ
```

### ステップ 6: CI パス後 → PR マージ

```bash
gh pr merge <pr-number> --squash
```

### ステップ 7: CD 監視（dev 環境デプロイ）

```bash
gh run list --branch main      # cd-dev.yml の実行を確認
gh run watch <run-id>          # デプロイ完了まで監視
```

`main` ブランチへのマージで `cd-dev.yml` が自動実行:
- Lint → Docker ビルド → Terraform Apply (dev) → Firebase Hosting deploy

### ステップ 8: CD 失敗時

```bash
gh run view <run-id> --log-failed
# → ログを確認して原因を特定・修正
```

### ステップ 9: デプロイ成功確認

- dev 環境 URL でアプリの動作を確認
- 必要に応じて `tests/e2e/` または `scripts/verify_*.sh` を dev 環境に対して実行

### prod リリース

```bash
git tag v1.0.0
git push origin v1.0.0
# → cd-prod-build.yml (Docker ビルド) → cd-prod-terraform.yml (Terraform apply prod)
```

---

## 7. コーディング規約

### Python

- **ruff**: `select = ["E","W","F","I","UP","B","SIM"]`, `target-version = "py313"`
- `E501`（行長）は無視（formatter に委ねる）
- `v2/entrypoints/api/**` と `worker.py` は `B008` を除外（FastAPI `Depends` パターンのため）

### フロントエンド

- **ESLint**: `next lint`（`eslint-config-next`）
- TypeScript strict mode
- スタイル: Tailwind CSS

### アーキテクチャ

- **Ports**: `v2/domain/ports.py` に ABC でインターフェースを定義
- **Adapters**: `v2/adapters/` に Ports の実装を配置
- **Null Object Pattern**: Todoist / Slack 未設定時は NullAdapter に差し替え
- **ドメインモデル**: `frozen=True` dataclass でイミュータブルに保つ
- **DI**: FastAPI の `Depends` + `dependency_overrides`（テスト時に差し替え）

### セキュリティ

- `.env.local` / `service_account.json` を絶対にコミットしない
- Firestore ルール: クライアント SDK 全拒否（Admin SDK のみ使用）
- WIF (Workload Identity Federation): 静的サービスアカウントキー不使用

---

## 8. CI/CD パイプライン概要

| トリガー | ワークフロー | 内容 |
|---|---|---|
| PR | `ci.yml` | lint + test (unit/integration/e2e) + Firestore rules |
| PR | `ci-frontend.yml` | Playwright E2E テスト |
| PR (terraform変更時) | `tf-cmt-dev.yml` | `terraform plan` コメント |
| `main` push | `cd-dev.yml` | Lint → Docker ビルド → Terraform Apply (dev) → Firebase Hosting deploy |
| `v*` タグ | `cd-prod-build.yml` | Docker ビルド & `latest-prod` タグ付与 |
| `v*` タグ | `cd-prod-terraform.yml` | Terraform Apply (prod) |

認証: **WIF (OIDC)** — 静的サービスアカウントキー不使用

---

## 9. GCP / Firebase プロジェクト

| 環境 | GCP / Firebase プロジェクト ID |
|---|---|
| dev | `clearbag-dev` |
| prod | `clearbag-prod` |

- Terraform backend バケット: `clearbag-dev-terraform-backend` / `clearbag-prod-terraform-backend`
- `PROJECT_ID` 環境変数のみ使用（`FIREBASE_PROJECT_ID` は廃止済み）

---

## 10. トラブルシューティング

### Firestore Emulator が起動しない

```bash
docker compose ps         # コンテナ状態を確認
docker compose logs       # ログを確認
make stop && make dev-infra  # 再起動
```

### `uv run pytest` でモジュールが見つからない

```bash
uv sync    # 依存関係を再インストール
```

### ruff が B008 エラーを出す

`v2/entrypoints/api/` 配下のファイルは FastAPI の `Depends()` パターンを使うため、`B008` は `pyproject.toml` で除外済み。それ以外のファイルで出た場合は `Depends` の使い方を見直す。

### `is_activated` エラー (403 ACTIVATION_REQUIRED)

```bash
PROJECT_ID=clearbag-dev uv run python scripts/activate_existing_users.py --email your@email.com
```
