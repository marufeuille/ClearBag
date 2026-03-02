terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  backend "gcs" {
    bucket = "clearbag-prod-terraform-backend"
    prefix = "terraform/environments/prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# プロジェクト情報
# ---------------------------------------------------------------------------

data "google_project" "project" {
  project_id = var.project_id
}

# Cloud Run Service Agent に Artifact Registry からのイメージ pull 権限を付与
# 新規プロジェクトではデフォルトで付与されないため明示的に設定が必要
resource "google_project_iam_member" "cloud_run_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

# ---------------------------------------------------------------------------
# Cloud Run Job 実行用 Service Account
# ---------------------------------------------------------------------------

resource "google_service_account" "cloud_run" {
  project      = var.project_id
  account_id   = "school-agent-v2-prod"
  display_name = "school-agent-v2 prod 実行用 SA"
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_service_account_iam_member" "scheduler_token_creator" {
  service_account_id = google_service_account.cloud_run.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
}

# Cloud Run SA が Cloud Tasks タスク作成時に自分自身に actAs するために必要
# （oidc_token.service_account_email に自 SA を指定するため serviceAccountUser が必要）
resource "google_service_account_iam_member" "cloud_run_self_actas" {
  service_account_id = google_service_account.cloud_run.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cloud_run.email}"
}

# ---------------------------------------------------------------------------
# Artifact Registry (prod 専用リポジトリ)
# ---------------------------------------------------------------------------

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "school-agent-prod"
  environment   = "prod"

  # IAM 付与 (repoAdmin) と artifact_registry リソース更新の race condition を防ぐため、
  # github_actions_prod IAM メンバーが確定してから artifact_registry を更新する
  depends_on = [google_project_iam_member.github_actions_prod]
}

module "monitoring" {
  source = "../../modules/monitoring"

  project_id         = var.project_id
  notification_email = var.notification_email

  # IAM 付与と monitoring リソース作成の race condition を防ぐため、
  # github_actions_prod IAM メンバーが確定してから monitoring を作成する
  depends_on = [google_project_iam_member.github_actions_prod]
}

# ---------------------------------------------------------------------------
# Workload Identity Federation (prod 専用)
# dev とは別の Pool/Provider/SA を作成し、独立して管理する
# ---------------------------------------------------------------------------

# WIF に必要な GCP API
resource "google_project_service" "sts" {
  project            = var.project_id
  service            = "sts.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iamcredentials" {
  project            = var.project_id
  service            = "iamcredentials.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudresourcemanager" {
  project            = var.project_id
  service            = "cloudresourcemanager.googleapis.com"
  disable_on_destroy = false
}

module "workload_identity" {
  source        = "../../modules/workload_identity"
  project_id    = var.project_id
  github_repo   = "marufeuille/ClearBag"
  pool_id       = "github-actions-prod"
  sa_account_id = "github-actions-deploy-prod"
  ref_condition = "assertion.ref == 'refs/heads/main' || assertion.ref.matches('refs/tags/v.*') || assertion.event_name == 'pull_request'"

  depends_on = [
    google_project_service.sts,
    google_project_service.iamcredentials,
  ]
}

# GitHub Actions prod SA に付与する IAM ロール
locals {
  github_actions_prod_roles = [
    "roles/artifactregistry.admin",          # Docker イメージ push + リポジトリ設定更新 (cleanup policy 等、repoAdmin は repositories.update を含まない)
    "roles/run.admin",                       # Cloud Run Job 更新・IAM ポリシー設定 (run.jobs.setIamPolicy が必要)
    "roles/iam.serviceAccountUser",          # Cloud Run SA として実行
    "roles/storage.admin",                   # Terraform state (GCS) 読み書き
    "roles/cloudscheduler.admin",            # Cloud Scheduler 管理
    "roles/resourcemanager.projectIamAdmin", # terraform が IAM ポリシーを変更するため
    "roles/secretmanager.admin",             # Secret Manager リソースの参照・管理
    "roles/serviceusage.serviceUsageAdmin",  # API 有効化 (google_project_service)
    "roles/iam.serviceAccountAdmin",         # SA の作成・管理
    "roles/iam.workloadIdentityPoolAdmin",   # WIF Pool/Provider の管理
    "roles/monitoring.admin",                # Cloud Monitoring アラートポリシー・通知チャンネル管理
    "roles/firebaserules.admin",             # Firestore セキュリティルール デプロイ
    "roles/datastore.owner",                 # Firestore 管理 (B2C)
    "roles/cloudtasks.admin",                # Cloud Tasks キュー管理 (B2C)
    "roles/firebasehosting.admin",           # Firebase Hosting デプロイ
  ]
}

resource "google_project_iam_member" "github_actions_prod" {
  for_each = toset(local.github_actions_prod_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${module.workload_identity.service_account_email}"
}

# ---------------------------------------------------------------------------
# B2C SaaS 基盤
# ---------------------------------------------------------------------------

# B2C に必要な GCP API
resource "google_project_service" "firestore" {
  project            = var.project_id
  service            = "firestore.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudtasks" {
  project            = var.project_id
  service            = "cloudtasks.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firebase" {
  project            = var.project_id
  service            = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firebasehosting" {
  project            = var.project_id
  service            = "firebasehosting.googleapis.com"
  disable_on_destroy = false
}

# Firebase Console 経由で既に作成された Firestore DB を Terraform state に取り込む
import {
  to = module.firestore.google_firestore_database.this
  id = "projects/clearbag-prod/databases/(default)"
}

module "firestore" {
  source = "../../modules/firestore"

  project_id            = var.project_id
  location              = var.region
  service_account_email = google_service_account.cloud_run.email
  deletion_policy       = "ABANDON"  # prod では誤削除防止のため ABANDON

  # IAM 付与と Firestore 作成の race condition を防ぐため、
  # github_actions_prod IAM メンバーが確定してから Firestore を作成する
  depends_on = [
    google_project_iam_member.github_actions_prod,
    google_project_service.firestore,
  ]
}

module "cloud_storage_uploads" {
  source = "../../modules/cloud_storage"

  project_id            = var.project_id
  bucket_name           = "${var.project_id}-clearbag-uploads-prod"
  service_account_email = google_service_account.cloud_run.email
  lifecycle_delete_days = 365
}

module "cloud_tasks_analysis" {
  source = "../../modules/cloud_tasks"

  project_id            = var.project_id
  queue_name            = "clearbag-analysis-prod"
  service_account_email = google_service_account.cloud_run.email

  # Gemini 2.5 Pro のレート制限に合わせて同時実行数を制限
  max_dispatches_per_second = 1
  max_concurrent_dispatches = 3

  # API 有効化と IAM 付与を待ってからキューを作成する
  depends_on = [
    google_project_iam_member.github_actions_prod,
    google_project_service.cloudtasks,
  ]
}

module "secret_vapid_private_key" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "clearbag-vapid-private-key-prod"
  service_account_email = google_service_account.cloud_run.email
}

module "api_service" {
  source = "../../modules/cloud_run_service"

  project_id            = var.project_id
  region                = var.region
  service_name          = "clearbag-api-prod"
  image_url             = var.api_image_url
  service_account_email = google_service_account.cloud_run.email
  allow_unauthenticated = true
  memory                = "1Gi"

  env_vars = {
    PROJECT_ID              = var.project_id
    GCS_BUCKET_NAME         = module.cloud_storage_uploads.bucket_name
    CLOUD_TASKS_QUEUE       = module.cloud_tasks_analysis.queue_id
    CLOUD_TASKS_LOCATION    = var.region
    VERTEX_AI_LOCATION      = var.region
    GEMINI_MODEL            = "gemini-2.5-pro"
    # iCal URL の組み立てに使用するベース URL（self-reference: apply後に確定）
    API_BASE_URL            = "https://clearbag-api-prod-${data.google_project.project.number}.${var.region}.run.app"
    # Cloud Tasks が解析ワーカーを呼び出すURL（self-reference: apply後に確定）
    WORKER_URL              = "https://clearbag-api-prod-${data.google_project.project.number}.${var.region}.run.app/worker/analyze"
    SERVICE_ACCOUNT_EMAIL        = google_service_account.cloud_run.email
    WORKER_SERVICE_ACCOUNT_EMAIL = google_service_account.cloud_run.email
    # ログイン許可メールアドレス（カンマ区切り）。未設定の場合は全員許可
    ALLOWED_EMAILS          = var.allowed_emails
    # prod では rate limit を有効化（DISABLE_RATE_LIMIT は設定しない）
    # Firebase Hosting のオリジン（カンマ区切り）
    CORS_ORIGINS            = "https://${var.project_id}.web.app,https://${var.project_id}.firebaseapp.com"
    FRONTEND_BASE_URL       = "https://${var.project_id}.firebaseapp.com"
    # Web Push VAPID クレームに使用する連絡先メールアドレス（非機密）
    VAPID_CLAIMS_EMAIL      = var.vapid_claims_email
  }

  secret_env_vars = {
    VAPID_PRIVATE_KEY = module.secret_vapid_private_key.secret_id
  }

  depends_on = [
    module.firestore,
    module.cloud_storage_uploads,
    module.cloud_tasks_analysis,
    module.secret_vapid_private_key,
  ]
}

# 朝のダイジェスト: 毎朝 7:30 JST に /worker/morning-digest を呼び出す
module "morning_digest_scheduler" {
  source = "../../modules/cloud_scheduler"

  project_id            = var.project_id
  region                = var.region
  job_name              = "clearbag-morning-digest-prod"
  schedule              = "30 7 * * *"
  time_zone             = "Asia/Tokyo"
  target_url            = "${module.api_service.service_url}/worker/morning-digest"
  service_account_email = google_service_account.cloud_run.email
  use_oidc              = true  # Cloud Run Service (run.app) の呼び出しには OIDC が必要

  depends_on = [module.api_service]
}

# イベントリマインダー: 毎晩 20:00 JST に /worker/event-reminder を呼び出す（翌日予定の前日通知）
module "event_reminder_scheduler" {
  source = "../../modules/cloud_scheduler"

  project_id            = var.project_id
  region                = var.region
  job_name              = "clearbag-event-reminder-prod"
  schedule              = "0 20 * * *"
  time_zone             = "Asia/Tokyo"
  target_url            = "${module.api_service.service_url}/worker/event-reminder"
  service_account_email = google_service_account.cloud_run.email
  use_oidc              = true

  depends_on = [module.api_service]
}

# ---------------------------------------------------------------------------
# 予算アラート
# ---------------------------------------------------------------------------

resource "google_project_service" "billingbudgets" {
  project            = var.project_id
  service            = "billingbudgets.googleapis.com"
  disable_on_destroy = false
}

# google_billing_budget は cloudbilling.googleapis.com API を使用する
resource "google_project_service" "cloudbilling" {
  project            = var.project_id
  service            = "cloudbilling.googleapis.com"
  disable_on_destroy = false
}

# 注意: GitHub Actions SA への roles/billing.costsManager 付与は手動で行う
# gcloud billing accounts add-iam-policy-binding BILLING_ACCOUNT_ID \
#   --member="serviceAccount:github-actions-deploy-prod@clearbag-prod.iam.gserviceaccount.com" \
#   --role="roles/billing.costsManager"
module "billing_budget" {
  source = "../../modules/billing_budget"

  billing_account_id        = var.billing_account_id
  project_id                = var.project_id
  budget_amount             = var.budget_amount
  currency_code             = var.currency_code
  notification_channel_name = module.monitoring.notification_channel_name

  depends_on = [
    google_project_iam_member.github_actions_prod,
    google_project_service.billingbudgets,
    google_project_service.cloudbilling,
  ]
}
