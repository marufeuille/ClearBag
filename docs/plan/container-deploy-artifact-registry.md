# コンテナベースデプロイ導入：Artifact Registry + build/push スクリプト

## Context

現状の `deploy_v2.sh` は `gcloud functions deploy --gen2 --runtime=python313 --source=.` によるソースベースデプロイを採用している。Cloud Build が内部でコンテナを生成するため、ビルド過程の制御や再現性に課題がある。

今後のCI/CD化・インフラのIaC化、およびdev/prod環境分離を見据え、以下を今回のスコープとして実装する：

1. **Artifact Registry** を Terraform module 構成で管理（dev 環境を先行実装）
2. **`build_push.sh`** — コンテナの build & Artifact Registry push を行うスクリプト

Cloud Function 本体のデプロイ方式変更（`--image` フラグへの移行）は別タスクとする。

---

## 現状のファイル構成

| ファイル | 役割 |
|----------|------|
| `Dockerfile` | 既存。python:3.13-slim ベース、functions-framework 起動 |
| `.dockerignore` | 既存。.git, tests/, docs/ 等を除外 |
| `deploy_v2.sh` | 既存のソースベースデプロイスクリプト（今回は変更しない） |
| `requirements.txt` | `uv export` で生成。Dockerfile の `COPY requirements.txt .` で使用 |

---

## 変更・追加対象ファイル

| ファイル | 操作 | 目的 |
|----------|------|------|
| `terraform/modules/artifact_registry/main.tf` | **新規作成** | Artifact Registry リソース定義（再利用可能なmodule） |
| `terraform/modules/artifact_registry/variables.tf` | **新規作成** | module の入力変数 |
| `terraform/modules/artifact_registry/outputs.tf` | **新規作成** | module の出力値 |
| `terraform/environments/dev/main.tf` | **新規作成** | dev 環境のエントリポイント。provider定義とmodule呼び出し |
| `terraform/environments/dev/variables.tf` | **新規作成** | dev 環境の変数定義 |
| `terraform/environments/dev/outputs.tf` | **新規作成** | dev 環境の出力値 |
| `build_push.sh` | **新規作成** | コンテナ build & push スクリプト |

---

## 1. Terraform 構成

### 1.1 全体ディレクトリ構造

```
terraform/
  modules/
    artifact_registry/    # 再利用可能なmodule（環境を知らない）
      main.tf
      variables.tf
      outputs.tf
  environments/
    dev/                  # dev 環境（今回実装）
      main.tf
      variables.tf
      outputs.tf
      terraform.tfvars    # ★ gitignore 対象（project_idを含む）
    prod/                 # prod 環境（将来実装）
      ...
```

**設計原則**：
- `modules/` は環境に依存しない純粋なリソース定義。環境の数に関わらず1つだけ存在する
- `environments/` は環境ごとに独立した `terraform init` / `state` を持つ
- dev/prod は GCPプロジェクトを分けることを想定（同一プロジェクトの場合は `repository_id` の命名で区別）

---

### 1.2 `terraform/modules/artifact_registry/variables.tf`

```hcl
variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "Artifact Registry のロケーション"
  type        = string
}

variable "repository_id" {
  description = "Artifact Registry リポジトリID"
  type        = string
}

variable "environment" {
  description = "環境名（ラベル用）"
  type        = string
}
```

### 1.3 `terraform/modules/artifact_registry/main.tf`

```hcl
resource "google_artifact_registry_repository" "this" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
  description   = "school-agent コンテナイメージリポジトリ (${var.environment})"

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}
```

### 1.4 `terraform/modules/artifact_registry/outputs.tf`

```hcl
output "registry_url" {
  description = "Artifact Registry の Docker リポジトリ URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}"
}

output "image_base" {
  description = "イメージ名のベース（タグなし）"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}/school-agent-v2"
}
```

---

### 1.5 `terraform/environments/dev/variables.tf`

```hcl
variable "project_id" {
  description = "dev 環境の GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "デプロイリージョン"
  type        = string
  default     = "asia-northeast1"
}
```

### 1.6 `terraform/environments/dev/main.tf`

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # 将来的にGCSバックエンドへ移行する（別タスク）
  # backend "gcs" {
  #   bucket = "YOUR_TFSTATE_BUCKET"
  #   prefix = "terraform/environments/dev"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "school-agent-dev"
  environment   = "dev"
}
```

### 1.7 `terraform/environments/dev/outputs.tf`

```hcl
output "registry_url" {
  description = "dev 環境の Artifact Registry URL"
  value       = module.artifact_registry.registry_url
}

output "image_base" {
  description = "dev 環境のイメージ名ベース"
  value       = module.artifact_registry.image_base
}
```

---

## 2. build_push.sh

### 2.1 責務

1. 環境名（`dev` / `prod`）を引数またはデフォルト値で受け取る
2. `.env` から `PROJECT_ID` を読み込む
3. `uv export` で `requirements.txt` を生成（Dockerfile が `COPY requirements.txt .` で使用するため）
4. イメージタグを決定（デフォルトは `git rev-parse --short HEAD`）
5. `docker build` でコンテナをビルド
6. `gcloud auth configure-docker` で Artifact Registry の認証設定
7. `docker push` でイメージをプッシュ
8. イメージURLを標準出力に出力（後続スクリプトや CI での利用を想定）

### 2.2 スクリプト仕様

```bash
#!/bin/bash
set -euo pipefail

# ==========================================
# Configuration
# ==========================================
REGION="asia-northeast1"
IMAGE_NAME="school-agent-v2"

# 引数: ENV（dev/prod）, IMAGE_TAG（任意）
ENV="${1:-dev}"
IMAGE_TAG="${2:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"

# 環境ごとのリポジトリID
case "$ENV" in
  dev)  REPOSITORY_ID="school-agent-dev" ;;
  prod) REPOSITORY_ID="school-agent" ;;
  *)    echo "Error: Unknown environment '$ENV'. Use 'dev' or 'prod'."; exit 1 ;;
esac

# Load environment variables
if [ -f .env ]; then
  export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# Check required
if [ -z "${PROJECT_ID:-}" ]; then
  echo "Error: PROJECT_ID is not set in .env"
  exit 1
fi

IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Environment : ${ENV}"
echo "Image URL   : ${IMAGE_URL}"

# ==========================================
# Preparation
# ==========================================
echo "Generating requirements.txt..."
uv export -o requirements.txt --no-hashes

# ==========================================
# Build
# ==========================================
echo "Building Docker image..."
docker build -t "${IMAGE_URL}" .

# ==========================================
# Push
# ==========================================
echo "Configuring Docker auth for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "Pushing image..."
docker push "${IMAGE_URL}"

echo ""
echo "Successfully pushed: ${IMAGE_URL}"
# 後続の処理から参照できるようにexportで出力
echo "IMAGE_URL=${IMAGE_URL}"
```

### 2.3 実行方法

```bash
# dev 環境へ push（git SHA タグ）
./build_push.sh dev

# dev 環境へ push（タグ明示指定）
./build_push.sh dev v1.0.0

# prod 環境へ push（将来）
./build_push.sh prod v1.0.0
```

---

## 3. Terraform 運用手順

### 初回セットアップ（dev）

```bash
cd terraform/environments/dev

# terraform.tfvars を作成（gitignore 対象）
cat > terraform.tfvars <<EOF
project_id = "YOUR_DEV_PROJECT_ID"
EOF

terraform init
terraform plan
terraform apply
```

### `.gitignore` に追加すべき項目

```
# Terraform
terraform/**/.terraform/
terraform/**/terraform.tfstate
terraform/**/terraform.tfstate.backup
terraform/**/terraform.tfvars
```

`**` を使うことで environments/dev と将来追加される environments/prod の両方に適用される。
`terraform.tfvars` は `project_id` を含むため gitignore 対象。各 `variables.tf` はデフォルト値のみ持つため commit 可。

---

## 4. 今後の移行ロードマップ

| フェーズ | 内容 |
|----------|------|
| **今回** | `terraform/modules/artifact_registry/` + `terraform/environments/dev/` + `build_push.sh` |
| 次回 | `deploy_v2.sh` を `--image` ベースに変更し、コンテナデプロイを実現 |
| 将来 | `terraform/environments/prod/` を追加し、prod 環境の Artifact Registry を構築 |
| 将来 | Cloud Function・Scheduler・Secret Manager を Terraform module 化して各 environment から呼び出す |
| 将来 | GCS バックエンドで Terraform State を管理 |
| 将来 | GitHub Actions で build/push + deploy を自動化 |

---

## 5. 検証手順

### Terraform の検証

```bash
cd terraform/environments/dev
terraform init
terraform validate        # 構文チェック
terraform plan            # 差分確認（apply は実施しない）
```

### build_push.sh の検証

```bash
# ビルドのみ（push しない）
uv export -o requirements.txt --no-hashes
docker build -t school-agent-v2:test .
docker run --rm school-agent-v2:test echo "startup ok"

# dev 環境へ push（PROJECT_ID が設定済みの場合）
./build_push.sh dev
```

### Artifact Registry への push 後確認

```bash
REGION="asia-northeast1"
gcloud artifacts docker images list \
  "${REGION}-docker.pkg.dev/${PROJECT_ID}/school-agent-dev" \
  --project="${PROJECT_ID}"
```
