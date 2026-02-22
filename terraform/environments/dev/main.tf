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

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "school-agent-dev"
  environment   = "dev"
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
    "roles/artifactregistry.writer",         # Docker イメージ push
    "roles/run.developer",                   # Cloud Run Job 更新
    "roles/iam.serviceAccountUser",          # Cloud Run SA として実行
    "roles/storage.admin",                   # Terraform state (GCS) 読み書き
    "roles/cloudscheduler.admin",            # Cloud Scheduler 管理
    "roles/resourcemanager.projectIamAdmin", # terraform が IAM ポリシーを変更するため
    "roles/secretmanager.admin",             # Secret Manager リソースの参照・管理
    "roles/serviceusage.serviceUsageAdmin",  # API 有効化 (google_project_service)
    "roles/iam.serviceAccountAdmin",         # SA の作成・管理
  ]
}

resource "google_project_iam_member" "github_actions" {
  for_each = toset(local.github_actions_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${module.workload_identity.service_account_email}"
}
