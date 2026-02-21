locals {
  effective_service_account = var.service_account_email != "" ? var.service_account_email : "${var.project_id}@appspot.gserviceaccount.com"
  prefixed_function_name    = "${var.prefix}${var.function_name}"
  function_uri              = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.function_name}:latest"
}

resource "google_cloudfunctions2_function" "function" {
  provider    = google-beta
  name        = local.prefixed_function_name
  location    = var.region
  description = "School Agent v2 - Cloud Functions Gen2"

  build_config {
    runtime           = var.runtime
    entry_point       = var.entry_point
    docker_repository = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
  }

  service_config {
    max_instance_count    = 1
    min_instance_count    = 0
    available_memory      = "${var.memory}MiB"
    timeout_seconds       = 60
    service_account_email = local.effective_service_account

    environment_variables = {
      PROJECT_ID        = var.env_vars.PROJECT_ID
      SPREADSHEET_ID    = var.env_vars.SPREADSHEET_ID
      INBOX_FOLDER_ID   = var.env_vars.INBOX_FOLDER_ID
      ARCHIVE_FOLDER_ID = var.env_vars.ARCHIVE_FOLDER_ID
    }

    secret_environment_variables {
      key        = "SLACK_BOT_TOKEN"
      secret     = data.google_secret_manager_secret.slack_bot_token.secret_id
      version    = "latest"
      project_id = var.project_id
    }

    secret_environment_variables {
      key        = "SLACK_CHANNEL_ID"
      secret     = data.google_secret_manager_secret.slack_channel_id.secret_id
      version    = "latest"
      project_id = var.project_id
    }

    secret_environment_variables {
      key        = "TODOIST_API_TOKEN"
      secret     = data.google_secret_manager_secret.todoist_api_token.secret_id
      version    = "latest"
      project_id = var.project_id
    }
  }

  labels = {
    app-name = "school-agent"
    version  = "v2"
  }
}

output "function_uri" {
  description = "The container image URI in Artifact Registry (not the Cloud Function HTTP endpoint)"
  value       = local.function_uri
}

output "service_account_email" {
  description = "The service account email used by the Cloud Function"
  value       = local.effective_service_account
}

output "function_url" {
  description = "The HTTPS URL of the Cloud Function"
  value       = google_cloudfunctions2_function.function.service_config[0].uri
}
