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
  oidc_audience         = "https://run.googleapis.com/"
  service_account_email = google_service_account.cloud_run.email
}
