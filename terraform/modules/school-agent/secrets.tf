data "google_secret_manager_secret" "slack_bot_token" {
  project   = var.project_id
  secret_id = "${var.prefix}school-agent-slack-bot-token"
}

data "google_secret_manager_secret" "slack_channel_id" {
  project   = var.project_id
  secret_id = "${var.prefix}school-agent-slack-channel-id"
}

data "google_secret_manager_secret" "todoist_api_token" {
  project   = var.project_id
  secret_id = "${var.prefix}school-agent-todoist-api-token"
}

resource "google_secret_manager_secret_iam_member" "slack_bot_token_accessor" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.slack_bot_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.effective_service_account}"
}

resource "google_secret_manager_secret_iam_member" "slack_channel_id_accessor" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.slack_channel_id.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.effective_service_account}"
}

resource "google_secret_manager_secret_iam_member" "todoist_api_token_accessor" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.todoist_api_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.effective_service_account}"
}
