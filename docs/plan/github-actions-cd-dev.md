# GitHub Actions CD ワークフロー (dev環境)

## Context

`deploy_dev.sh` により dev 環境のビルド＆デプロイが1コマンドで実行可能になった。次のステップとして、main ブランチへのマージ時に同等の処理を GitHub Actions で自動実行する CD パイプラインを構築する。

現状の課題:
- デプロイが手動（ローカルで `deploy_dev.sh` を実行）
- Terraform state がローカルファイル → CI/CD では共有不可
- GCP 認証がローカルの `gcloud` に依存 → GitHub Actions では使えない

## スコープ

1. **Workload Identity Federation (WIF)** — GitHub Actions → GCP 認証基盤
2. **Terraform GCS バックエンド移行** — state のリモート管理
3. **GitHub Actions CD ワークフロー** — main push 時に自動デプロイ

---

## Phase 1: WIF (Workload Identity Federation) Terraform モジュール

### 新規: `terraform/modules/workload_identity/`

WIF の Pool / Provider / SA を作成するモジュール。

**変数:**
- `project_id` (string)
- `github_repo` (string) — `"marufeuille/ClearBag"`

**リソース:**
- `google_iam_workload_identity_pool` — Pool `github-actions`
- `google_iam_workload_identity_pool_provider` — OIDC Provider for GitHub
  - `issuer_uri = "https://token.actions.githubusercontent.com"`
  - `attribute_condition = "assertion.repository == 'marufeuille/ClearBag'"` （他リポジトリからの認証を防止）
  - `attribute_mapping`: `google.subject` → `assertion.sub`, `attribute.repository` → `assertion.repository`
- `google_service_account` — デプロイ専用 SA `github-actions-deploy`
- `google_service_account_iam_member` — WIF Pool → SA の workloadIdentityUser バインディング

**出力:**
- `workload_identity_provider` — Provider のフルパス（GitHub Secrets に登録）
- `service_account_email` — SA メールアドレス（GitHub Secrets に登録）

### 変更: `terraform/environments/dev/main.tf`

WIF モジュール呼び出しと、デプロイ SA への IAM ロール付与を追加:

```hcl
module "workload_identity" {
  source      = "../../modules/workload_identity"
  project_id  = var.project_id
  github_repo = "marufeuille/ClearBag"
}
```

**デプロイ SA に付与するロール:**
| ロール | 用途 |
|--------|------|
| `roles/artifactregistry.writer` | Docker イメージ push |
| `roles/run.developer` | Cloud Run Job 更新 |
| `roles/iam.serviceAccountUser` | Cloud Run SA として実行 |
| `roles/storage.admin` | Terraform state (GCS) 読み書き |
| `roles/cloudscheduler.admin` | Cloud Scheduler 管理 |

---

## Phase 2: Terraform GCS バックエンド移行

### 手順 (ローカルで実行)

1. GCS バケット `marufeuille-linebot-terraform-backend` は既存のものを使用する。

2. `terraform/environments/dev/main.tf` の backend ブロックを有効化:
   ```hcl
   backend "gcs" {
     bucket = "marufeuille-linebot-terraform-backend"
     prefix = "terraform/environments/dev"
   }
   ```

3. State 移行:
   ```bash
   cd terraform/environments/dev
   terraform init -migrate-state
   ```

---

## Phase 3: GitHub Actions CD ワークフロー

### 新規: `.github/workflows/cd-dev.yml`

**トリガー:** `push` to `main`（PR マージを含む）

**ジョブ構成:**

```
lint → ─┐
        ├─→ deploy
test → ─┘
```

#### `lint` ジョブ (既存 ci.yml と同等)
- checkout → setup-uv → setup-python 3.13 → `uv sync --extra dev`
- `ruff check v2/` + `ruff format --check v2/`

#### `test` ジョブ (既存 ci.yml と同等)
- checkout → setup-uv → setup-python 3.13 → `uv sync --extra dev`
- `pytest tests/unit/ tests/integration/ -m "not manual" --cov=v2`

#### `deploy` ジョブ (`needs: [lint, test]`)
- `permissions: id-token: write` （WIF OIDC トークン発行に必要）
- `environment: dev` （GitHub Environment 保護ルールに対応可能）
- `concurrency: group: deploy-dev` （同時デプロイ防止）

**ステップ:**
1. `actions/checkout@v4`
2. `google-github-actions/auth@v2` — WIF 認証
   - `workload_identity_provider: ${{ secrets.WIF_PROVIDER }}`
   - `service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}`
3. `google-github-actions/setup-gcloud@v2`
4. `gcloud auth configure-docker asia-northeast1-docker.pkg.dev`
5. `astral-sh/setup-uv@v5` → `uv export -o requirements.txt --no-hashes`
6. Docker build (`--platform linux/amd64`, タグ: `${GITHUB_SHA::7}` + `latest`)
7. Docker push (SHA タグ + latest)
8. `hashicorp/setup-terraform@v3`
9. `terraform init` (working-directory: `terraform/environments/dev`)
10. `terraform apply -auto-approve` — `-var` で全変数を渡す

**Terraform 変数の渡し方:**
| 変数 | 渡し方 |
|------|--------|
| `image_url` | ステップ6で構築した `IMAGE_URL` (env) |
| `project_id` | ワークフロー `env` で定数定義 |
| `spreadsheet_id` | `${{ secrets.TF_VAR_SPREADSHEET_ID }}` |
| `inbox_folder_id` | `${{ secrets.TF_VAR_INBOX_FOLDER_ID }}` |
| `archive_folder_id` | `${{ secrets.TF_VAR_ARCHIVE_FOLDER_ID }}` |

### GitHub Secrets 設定

| Secret 名 | 値 |
|------------|-----|
| `WIF_PROVIDER` | Terraform output `workload_identity_provider` |
| `WIF_SERVICE_ACCOUNT` | Terraform output `service_account_email` |
| `TF_VAR_SPREADSHEET_ID` | `terraform.tfvars` の値 |
| `TF_VAR_INBOX_FOLDER_ID` | `terraform.tfvars` の値 |
| `TF_VAR_ARCHIVE_FOLDER_ID` | `terraform.tfvars` の値 |

---

## 実装順序

| # | 作業 | 実行場所 | 備考 |
|---|------|----------|------|
| 1 | WIF Terraform モジュール作成 | ローカル | `terraform/modules/workload_identity/` |
| 2 | dev/main.tf に WIF + IAM 追加 | ローカル | モジュール呼び出し + ロール付与 |
| 3 | `terraform apply` (ローカル) | ローカル | WIF リソースを GCP に作成 |
| 4 | GCS バケット確認 | ローカル (gcloud) | `marufeuille-linebot-terraform-backend` を使用 |
| 5 | GCS backend 有効化 + state 移行 | ローカル | `terraform init -migrate-state` |
| 6 | GitHub Secrets 設定 | GitHub UI | WIF_PROVIDER, WIF_SERVICE_ACCOUNT, TF_VAR_* |
| 7 | `cd-dev.yml` 作成 | PR | CD ワークフローファイル |
| 8 | main にマージして動作確認 | GitHub | E2E 検証 |

**Step 1〜5 はローカルでのブートストラップ作業**（GitHub Actions が動くための前提条件を整える）。Step 6〜8 は通常の PR フローで実行可能。

---

## 変更対象ファイル

| ファイル | 操作 |
|----------|------|
| `terraform/modules/workload_identity/main.tf` | 新規作成 |
| `terraform/modules/workload_identity/variables.tf` | 新規作成 |
| `terraform/modules/workload_identity/outputs.tf` | 新規作成 |
| `terraform/environments/dev/main.tf` | 変更 (WIF モジュール + IAM + GCS backend) |
| `.github/workflows/cd-dev.yml` | 新規作成 |

---

## 検証方法

1. **WIF 認証テスト**: ワークフロー実行後、`Authenticate to GCP via WIF` ステップが成功すること
2. **Docker build/push**: Artifact Registry に SHA タグ付きイメージが push されること
3. **Terraform apply**: `terraform apply` が正常完了し、Cloud Run Job のイメージが更新されること
4. **E2E**: Cloud Scheduler によるジョブ実行が引き続き正常に動作すること
5. **ロールバック**: 既存の `deploy_dev.sh` でのローカルデプロイも引き続き動作すること（GCS backend に移行済みなので互換性あり）
