# コンテナデプロイ移行: Cloud Run Jobs への切り替え（dev 環境）

## 改版履歴

| 版 | 日付 | 変更内容 |
|---|---|---|
| v1 | 2026-02-22 | 初版（Cloud Run Service） |
| v2 | 2026-02-22 | 命名規則統一（全リソースに `-dev` suffix）・既存シークレット移行手順追加 |
| v3 | 2026-02-22 | `deletion_protection = false` 追加・`build_push.sh` に `latest` tag push を追加 |
| v4 | 2026-02-22 | **Cloud Run Service → Cloud Run Jobs へ全面移行**。Dockerfile CMD 変更、Scheduler OIDC 修正 |

---

## Context

このアプリ（`school-agent-v2`）は **バッチジョブ**である：
- Cloud Scheduler が朝9時・夕17時に起動
- `orchestrator.run()` でファイル処理・Slack通知・Todoist登録を実行
- 処理が終わったらプロセスが終了する（HTTPサーバーとして常駐しない）

**Cloud Run Service**（HTTP サーバー）ではなく **Cloud Run Jobs**（バッチ実行）が適切。

| 項目 | Cloud Run Service（旧） | Cloud Run Jobs（新） |
|---|---|---|
| エントリーポイント | `functions-framework`（HTTP サーバー） | `python -m v2.entrypoints.cli`（CLIバッチ） |
| Scheduler 連携 | HTTP POST → Service URL | Jobs API（`：run`）→ Job 実行 |
| 終了方式 | アイドルでスケールダウン | 処理完了 → コンテナ終了 |
| OIDC audience | サービス URL | `https://run.googleapis.com/` |
| 実行 URL | `.run.app` | なし（API 経由のみ） |

**既存コード `v2/entrypoints/cli.py`** は `orchestrator.run()` → `sys.exit()` の形式で Cloud Run Jobs にそのまま使える。

---

## アーキテクチャ概要

```
Cloud Scheduler (0 9,17 * * *)
  → HTTP POST https://run.googleapis.com/v2/.../jobs/school-agent-v2-dev:run
  → OIDC トークン（audience = https://run.googleapis.com/）
  → Cloud Run Job: school-agent-v2-dev
      → docker run python -m v2.entrypoints.cli
      → 処理完了 → exit 0
```

---

## Terraform 管理リソース（完成形）

```
terraform/environments/dev/
  └── google_service_account "cloud_run"   ← SA（作成済み）
  └── module "artifact_registry"            ← 実装済み
  └── module "secret_*" × 3                ← 実装済み
  └── module "cloud_run_job"               ← 今回 cloud_run → cloud_run_job に置き換え
  └── module "cloud_scheduler"             ← OIDC audience・URI を変更
```

---

## 変更・追加対象ファイル

| ファイル | 操作 | 変更内容 |
|---|---|---|
| `terraform/modules/cloud_run_job/variables.tf` | **新規作成** | Job module 入力変数 |
| `terraform/modules/cloud_run_job/main.tf` | **新規作成** | `google_cloud_run_v2_job` + IAM |
| `terraform/modules/cloud_run_job/outputs.tf` | **新規作成** | `job_name`, `job_api_uri` の出力 |
| `terraform/modules/cloud_run/` | **ディレクトリ削除** | Service module は不要 |
| `terraform/modules/cloud_scheduler/variables.tf` | **修正** | `oidc_audience` 変数を追加 |
| `terraform/modules/cloud_scheduler/main.tf` | **修正** | OIDC audience を `var.oidc_audience` に変更 |
| `terraform/environments/dev/main.tf` | **修正** | `cloud_run` → `cloud_run_job`、Scheduler の URL・audience を更新 |
| `terraform/environments/dev/outputs.tf` | **修正** | `service_url` を削除、`job_name` を追加 |
| `Dockerfile` | **修正** | `CMD` を `python -m v2.entrypoints.cli` に変更 |
| `deploy_dev.sh` | **修正** | `terraform output service_url` を削除 |

---

## 1. Terraform module: cloud_run_job（新規）

### 1.1 `terraform/modules/cloud_run_job/variables.tf`

```hcl
variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "Cloud Run Job のリージョン"
  type        = string
}

variable "job_name" {
  description = "Cloud Run Job 名"
  type        = string
}

variable "image_url" {
  description = "デプロイするコンテナイメージの URL"
  type        = string
}

variable "service_account_email" {
  description = "Job 実行に使用するサービスアカウント（空の場合はデフォルト Compute SA）"
  type        = string
  default     = ""
}

variable "invoker_service_account_email" {
  description = "Job を起動する権限（roles/run.invoker）を付与するサービスアカウント"
  type        = string
}

variable "memory" {
  description = "コンテナに割り当てるメモリ量"
  type        = string
  default     = "1Gi"
}

variable "cpu" {
  description = "コンテナに割り当てる CPU 数"
  type        = string
  default     = "1"
}

variable "max_retries" {
  description = "タスク失敗時の最大リトライ数（0 = リトライなし）"
  type        = number
  default     = 0
}

variable "timeout" {
  description = "タスクのタイムアウト（例: 3600s = 1時間）"
  type        = string
  default     = "3600s"
}

variable "env_vars" {
  description = "通常の環境変数マッピング（key: 環境変数名, value: 値）"
  type        = map(string)
  default     = {}
}

variable "secret_env_vars" {
  description = "Secret Manager から注入する環境変数マッピング（key: 環境変数名, value: Secret ID）"
  type        = map(string)
  default     = {}
}
```

### 1.2 `terraform/modules/cloud_run_job/main.tf`

```hcl
resource "google_cloud_run_v2_job" "this" {
  project  = var.project_id
  name     = var.job_name
  location = var.region

  deletion_protection = false

  template {
    task_count = 1

    template {
      service_account = var.service_account_email != "" ? var.service_account_email : null
      max_retries     = var.max_retries
      timeout         = var.timeout

      containers {
        image = var.image_url

        resources {
          limits = {
            memory = var.memory
            cpu    = var.cpu
          }
        }

        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = var.secret_env_vars
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.this.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.invoker_service_account_email}"
}
```

### 1.3 `terraform/modules/cloud_run_job/outputs.tf`

```hcl
output "job_name" {
  description = "Cloud Run Job 名"
  value       = google_cloud_run_v2_job.this.name
}

output "job_api_uri" {
  description = "Cloud Scheduler から呼び出す Jobs API URI"
  value       = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.this.name}:run"
}
```

---

## 2. Terraform module: cloud_scheduler（修正）

Cloud Run Jobs の OIDC audience は **`https://run.googleapis.com/`**（サービス URL ではない）。
`oidc_audience` 変数を追加し、デフォルトは後方互換のため `var.target_url` とする。

### 2.1 `terraform/modules/cloud_scheduler/variables.tf`（修正）

既存変数はそのまま維持し、`oidc_audience` を追加:

```hcl
variable "oidc_audience" {
  description = "OIDC トークンの audience（Cloud Run Jobs の場合は https://run.googleapis.com/）"
  type        = string
  default     = ""  # 空の場合は target_url を使用
}
```

### 2.2 `terraform/modules/cloud_scheduler/main.tf`（修正）

```hcl
oidc_token {
  service_account_email = var.service_account_email
  audience              = var.oidc_audience != "" ? var.oidc_audience : var.target_url
}
```

---

## 3. Terraform dev 環境の更新

### 3.1 `terraform/environments/dev/main.tf`

`module "cloud_run"` を `module "cloud_run_job"` に置き換え、Cloud Scheduler の呼び出し先を更新する。

```hcl
# ==========================================
# Cloud Run Job（cloud_run → cloud_run_job に変更）
# ==========================================
module "cloud_run_job" {
  source = "../../modules/cloud_run_job"

  project_id                    = var.project_id
  region                        = var.region
  job_name                      = "school-agent-v2-dev"
  image_url                     = var.image_url
  service_account_email         = google_service_account.cloud_run.email
  invoker_service_account_email = google_service_account.cloud_run.email

  env_vars = {
    PROJECT_ID        = var.project_id
    SPREADSHEET_ID    = var.spreadsheet_id
    INBOX_FOLDER_ID   = var.inbox_folder_id
    ARCHIVE_FOLDER_ID = var.archive_folder_id
  }

  secret_env_vars = {
    SLACK_BOT_TOKEN   = module.secret_slack_bot_token.secret_id
    SLACK_CHANNEL_ID  = module.secret_slack_channel_id.secret_id
    TODOIST_API_TOKEN = module.secret_todoist_api_token.secret_id
  }

  depends_on = [
    module.secret_slack_bot_token,
    module.secret_slack_channel_id,
    module.secret_todoist_api_token,
  ]
}

# ==========================================
# Cloud Scheduler（Jobs API URI + audience 修正）
# ==========================================
module "cloud_scheduler" {
  source = "../../modules/cloud_scheduler"

  project_id            = var.project_id
  region                = var.region
  job_name              = "school-agent-v2-scheduler-dev"
  schedule              = "0 9,17 * * *"
  time_zone             = "Asia/Tokyo"
  target_url            = module.cloud_run_job.job_api_uri
  oidc_audience         = "https://run.googleapis.com/"
  service_account_email = google_service_account.cloud_run.email
}
```

### 3.2 `terraform/environments/dev/outputs.tf`

`service_url` を `job_name` に置き換える:

```hcl
output "registry_url" {
  description = "dev 環境の Artifact Registry URL"
  value       = module.artifact_registry.registry_url
}

output "image_base" {
  description = "dev 環境のイメージ名ベース"
  value       = module.artifact_registry.image_base
}

output "job_name" {
  description = "dev 環境の Cloud Run Job 名"
  value       = module.cloud_run_job.job_name
}

output "service_account_email" {
  description = "dev 環境の Cloud Run 実行 SA メールアドレス"
  value       = google_service_account.cloud_run.email
}
```

---

## 4. Dockerfile の変更

`functions-framework`（HTTP サーバー）から CLI バッチエントリーポイントへ変更。
`main_v2.py` のコピーも不要になる。

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "v2.entrypoints.cli"]
```

---

## 5. build_push.sh の仕様（変更なし）

versioned tag + `latest` tag の push は v3 の実装をそのまま維持する。

---

## 6. deploy_dev.sh の修正

`terraform output service_url` を `terraform output job_name` に変更する:

```bash
#!/bin/bash
set -euo pipefail

ENV="dev"
IMAGE_TAG="${1:-}"

if [ -f .env ]; then
  export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

echo "--- Build & Push ---"
BUILD_OUTPUT=$(./build_push.sh "${ENV}" ${IMAGE_TAG:+"${IMAGE_TAG}"})
echo "${BUILD_OUTPUT}"

IMAGE_URL=$(echo "${BUILD_OUTPUT}" | grep '^IMAGE_URL=' | cut -d'=' -f2-)
if [ -z "${IMAGE_URL}" ]; then
  echo "Error: Could not extract IMAGE_URL from build_push.sh output"
  exit 1
fi

echo ""
echo "--- Terraform Apply ---"
echo "Image: ${IMAGE_URL}"

cd terraform/environments/dev
terraform apply -var="image_url=${IMAGE_URL}" -auto-approve

echo ""
echo "Deployment finished."
terraform output job_name
```

---

## 7. 初回セットアップ手順（dev 環境）

### Step 0: Terraform state の確認と既存リソースの整理

前回の apply（Cloud Run Service の試みが失敗した可能性あり）でどの state が残っているか確認:

```bash
cd terraform/environments/dev
terraform state list
```

`module.cloud_run` が state に残っている場合は削除:

```bash
# state に残っている場合
terraform state rm module.cloud_run.google_cloud_run_v2_service.this
terraform state rm module.cloud_run.google_cloud_run_v2_service_iam_member.invoker
```

既存シークレット（dev suffix なし）の値を新シークレットに移行:

```bash
SLACK_BOT_TOKEN=$(gcloud secrets versions access latest \
  --secret="school-agent-slack-bot-token" --project="$PROJECT_ID")
SLACK_CHANNEL_ID=$(gcloud secrets versions access latest \
  --secret="school-agent-slack-channel-id" --project="$PROJECT_ID")
TODOIST_API_TOKEN=$(gcloud secrets versions access latest \
  --secret="school-agent-todoist-api-token" --project="$PROJECT_ID")
```

### Step 1: terraform.tfvars を作成（初回のみ）

```bash
cat > terraform/environments/dev/terraform.tfvars <<EOF
project_id        = "YOUR_DEV_PROJECT_ID"
spreadsheet_id    = "YOUR_SPREADSHEET_ID"
inbox_folder_id   = "YOUR_INBOX_FOLDER_ID"
archive_folder_id = "YOUR_ARCHIVE_FOLDER_ID"
# image_url は deploy_dev.sh が -var で渡すため不要
EOF
```

### Step 2: Secret 値の登録（apply 後・初回のみ）

```bash
echo -n "$SLACK_BOT_TOKEN" | \
  gcloud secrets versions add school-agent-slack-bot-token-dev \
    --data-file=- --project="$PROJECT_ID"

echo -n "$SLACK_CHANNEL_ID" | \
  gcloud secrets versions add school-agent-slack-channel-id-dev \
    --data-file=- --project="$PROJECT_ID"

echo -n "$TODOIST_API_TOKEN" | \
  gcloud secrets versions add school-agent-todoist-api-token-dev \
    --data-file=- --project="$PROJECT_ID"
```

### Step 3: 初回デプロイ

```bash
./deploy_dev.sh

# 確認
cd terraform/environments/dev && terraform output job_name
```

### Step 4: 2回目以降（通常デプロイ）

```bash
./deploy_dev.sh          # git SHA タグで自動デプロイ
./deploy_dev.sh v1.0.0   # タグ明示
```

---

## 8. 検証手順（実環境に影響しない範囲）

```bash
# Terraform 構文チェック
cd terraform/environments/dev
terraform validate

# deploy_dev.sh 構文チェック
bash -n deploy_dev.sh
```

---

## 9. 今後のロードマップ

| フェーズ | 内容 |
|---|---|
| **今回** | Cloud Run Jobs + Scheduler + Secret Manager。`deploy_dev.sh` でワンコマンドデプロイ |
| 次回 | `deploy_v2.sh` の削除・整理 |
| 将来 | `terraform/environments/prod/` を追加（prod 環境） |
| 将来 | 実行 SA と呼び出し SA を分離（セキュリティ強化） |
| 将来 | GitHub Actions で `deploy_dev.sh` を自動化 |
| 将来 | GCS バックエンドで Terraform State を管理 |
