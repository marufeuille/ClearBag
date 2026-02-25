terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  backend "gcs" {
    bucket = "marufeuille-linebot-terraform-backend"
    prefix = "terraform/environments/dev"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "cloud_run" {
  project      = var.project_id
  account_id   = "school-agent-v2-dev"
  display_name = "school-agent-v2 dev 実行用 SA"
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

data "google_project" "project" {
  project_id = var.project_id
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

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "school-agent-dev"
  environment   = "dev"

  # IAM 付与 (repoAdmin) と artifact_registry リソース更新の race condition を防ぐため、
  # github_actions IAM メンバーが確定してから artifact_registry を更新する
  depends_on = [google_project_iam_member.github_actions]
}

module "secret_slack_bot_token" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "school-agent-slack-bot-token-dev"
  service_account_email = google_service_account.cloud_run.email
}

module "secret_slack_channel_id" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "school-agent-slack-channel-id-dev"
  service_account_email = google_service_account.cloud_run.email
}

module "secret_todoist_api_token" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "school-agent-todoist-api-token-dev"
  service_account_email = google_service_account.cloud_run.email
}

module "cloud_run_job" {
  source = "../../modules/cloud_run_job"

  project_id                    = var.project_id
  region                        = var.region
  job_name                      = "school-agent-v2-dev"
  image_url                     = var.image_url
  service_account_email         = google_service_account.cloud_run.email
  invoker_service_account_email = google_service_account.cloud_run.email

  # API サーバーと同一イメージを使用し、バッチ CLI を起動するよう上書き
  command = ["python", "-m", "v2.entrypoints.cli"]

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

module "cloud_scheduler" {
  source = "../../modules/cloud_scheduler"

  project_id            = var.project_id
  region                = var.region
  job_name              = "school-agent-v2-scheduler-dev"
  schedule              = "0 9,17 * * *"
  time_zone             = "Asia/Tokyo"
  target_url            = module.cloud_run_job.job_api_uri
  service_account_email = google_service_account.cloud_run.email
}

module "monitoring" {
  source = "../../modules/monitoring"

  project_id         = var.project_id
  job_name           = module.cloud_run_job.job_name
  notification_email = var.notification_email

  # IAM 付与と monitoring リソース作成の race condition を防ぐため、
  # github_actions IAM メンバーが確定してから monitoring を作成する
  depends_on = [google_project_iam_member.github_actions]
}

# ---------------------------------------------------------------------------
# Workload Identity Federation (WIF) — GitHub Actions 用 GCP 認証基盤
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
  source      = "../../modules/workload_identity"
  project_id  = var.project_id
  github_repo = "marufeuille/ClearBag"

  depends_on = [
    google_project_service.sts,
    google_project_service.iamcredentials,
  ]
}

locals {
  github_actions_roles = [
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
    "roles/datastore.owner",                 # Firestore 管理 (B2C)
    "roles/cloudtasks.admin",                # Cloud Tasks キュー管理 (B2C)
    "roles/firebasehosting.admin",           # Firebase Hosting デプロイ
  ]
}

resource "google_project_iam_member" "github_actions" {
  for_each = toset(local.github_actions_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${module.workload_identity.service_account_email}"
}

# ---------------------------------------------------------------------------
# B2C SaaS 基盤 (Phase 1〜4 で追加)
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

# 既存の Firestore (default) データベースを Terraform state に取り込む
# 前回の apply で作成済みのため 409 が発生するのを防ぐ
import {
  to = module.firestore.google_firestore_database.this
  id = "projects/marufeuille-linebot/databases/(default)"
}

module "firestore" {
  source = "../../modules/firestore"

  project_id            = var.project_id
  location              = var.region
  service_account_email = google_service_account.cloud_run.email

  # IAM 付与と Firestore 作成の race condition を防ぐため、
  # github_actions IAM メンバーが確定してから Firestore を作成する
  depends_on = [
    google_project_iam_member.github_actions,
    google_project_service.firestore,
  ]
}

module "cloud_storage_uploads" {
  source = "../../modules/cloud_storage"

  project_id            = var.project_id
  bucket_name           = "${var.project_id}-clearbag-uploads-dev"
  service_account_email = google_service_account.cloud_run.email
  lifecycle_delete_days = 180
}

module "cloud_tasks_analysis" {
  source = "../../modules/cloud_tasks"

  project_id            = var.project_id
  queue_name            = "clearbag-analysis-dev"
  service_account_email = google_service_account.cloud_run.email

  # Gemini 2.5 Pro のレート制限に合わせて同時実行数を制限
  max_dispatches_per_second = 1
  max_concurrent_dispatches = 3

  # API 有効化と IAM 付与を待ってからキューを作成する
  depends_on = [
    google_project_iam_member.github_actions,
    google_project_service.cloudtasks,
  ]
}

module "secret_sendgrid_api_key" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "clearbag-sendgrid-api-key-dev"
  service_account_email = google_service_account.cloud_run.email
}

module "secret_vapid_private_key" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "clearbag-vapid-private-key-dev"
  service_account_email = google_service_account.cloud_run.email
}

module "api_service" {
  source = "../../modules/cloud_run_service"

  project_id            = var.project_id
  region                = var.region
  service_name          = "clearbag-api-dev"
  image_url             = var.api_image_url
  service_account_email = google_service_account.cloud_run.email
  allow_unauthenticated = true
  memory                = "1Gi"

  env_vars = {
    PROJECT_ID              = var.project_id
    FIREBASE_PROJECT_ID     = var.firebase_project_id
    GCS_BUCKET_NAME         = module.cloud_storage_uploads.bucket_name
    CLOUD_TASKS_QUEUE       = module.cloud_tasks_analysis.queue_id
    CLOUD_TASKS_LOCATION    = var.region
    VERTEX_AI_LOCATION      = var.region
    GEMINI_MODEL            = "gemini-2.5-pro"
    # Cloud Tasks が解析ワーカーを呼び出すURL（self-reference: apply後に確定）
    WORKER_URL              = "https://clearbag-api-dev-${data.google_project.project.number}.${var.region}.run.app/worker/analyze"
    SERVICE_ACCOUNT_EMAIL   = google_service_account.cloud_run.email
    # ログイン許可メールアドレス（カンマ区切り）。未設定の場合は全員許可
    ALLOWED_EMAILS          = var.allowed_emails
    # Firebase Hosting のオリジン（カンマ区切り）
    CORS_ORIGINS            = "https://${var.firebase_project_id}.web.app,https://${var.firebase_project_id}.firebaseapp.com"
  }

  # SENDGRID_API_KEY / VAPID_PRIVATE_KEY は Secret Manager にまだ値が未登録のため
  # 一旦無効化。登録後に secret_env_vars に戻す。
  secret_env_vars = {}

  depends_on = [
    module.firestore,
    module.cloud_storage_uploads,
    module.cloud_tasks_analysis,
    module.secret_sendgrid_api_key,
    module.secret_vapid_private_key,
  ]
}

# 朝のダイジェストメール: 毎朝 7:30 JST に /worker/morning-digest を呼び出す
module "morning_digest_scheduler" {
  source = "../../modules/cloud_scheduler"

  project_id            = var.project_id
  region                = var.region
  job_name              = "clearbag-morning-digest-dev"
  schedule              = "30 7 * * *"
  time_zone             = "Asia/Tokyo"
  target_url            = "${module.api_service.service_url}/worker/morning-digest"
  service_account_email = google_service_account.cloud_run.email
  use_oidc              = true  # Cloud Run Service (run.app) の呼び出しには OIDC が必要

  depends_on = [module.api_service]
}
