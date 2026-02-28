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

# ---------------------------------------------------------------------------
# Secret Manager
# ---------------------------------------------------------------------------

module "secret_slack_bot_token" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "school-agent-slack-bot-token-prod"
  service_account_email = google_service_account.cloud_run.email
}

module "secret_slack_channel_id" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "school-agent-slack-channel-id-prod"
  service_account_email = google_service_account.cloud_run.email
}

module "secret_todoist_api_token" {
  source = "../../modules/secret_manager"

  project_id            = var.project_id
  secret_id             = "school-agent-todoist-api-token-prod"
  service_account_email = google_service_account.cloud_run.email
}

# ---------------------------------------------------------------------------
# Cloud Run Job
# ---------------------------------------------------------------------------

module "cloud_run_job" {
  source = "../../modules/cloud_run_job"

  project_id                    = var.project_id
  region                        = var.region
  job_name                      = "school-agent-v2-prod"
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

# ---------------------------------------------------------------------------
# Cloud Scheduler
# ---------------------------------------------------------------------------

module "cloud_scheduler" {
  source = "../../modules/cloud_scheduler"

  project_id            = var.project_id
  region                = var.region
  job_name              = "school-agent-v2-scheduler-prod"
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
  # github_actions_prod IAM メンバーが確定してから monitoring を作成する
  depends_on = [google_project_iam_member.github_actions_prod]
}

# ---------------------------------------------------------------------------
# Workload Identity Federation (prod 専用)
# dev とは別の Pool/Provider/SA を作成し、独立して管理する
# ---------------------------------------------------------------------------

module "workload_identity" {
  source        = "../../modules/workload_identity"
  project_id    = var.project_id
  github_repo   = "marufeuille/ClearBag"
  pool_id       = "github-actions-prod"
  sa_account_id = "github-actions-deploy-prod"
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
  ]
}

resource "google_project_iam_member" "github_actions_prod" {
  for_each = toset(local.github_actions_prod_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${module.workload_identity.service_account_email}"
}
