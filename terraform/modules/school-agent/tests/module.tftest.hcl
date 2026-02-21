mock_provider "google" {}
mock_provider "google-beta" {}

# dev: prefix="dev-" でリソース名に接頭辞が付き、scheduler が paused になることを検証
run "dev_prefix_and_paused_scheduler" {
  variables {
    project_id       = "test-project"
    prefix           = "dev-"
    scheduler_paused = true
    env_vars = {
      PROJECT_ID        = "test-project"
      SPREADSHEET_ID    = "dummy-sheet"
      INBOX_FOLDER_ID   = "dummy-inbox"
      ARCHIVE_FOLDER_ID = "dummy-archive"
    }
  }

  command = plan

  assert {
    condition     = google_cloudfunctions2_function.function.name == "dev-school-agent-v2"
    error_message = "dev環境ではFunction名に'dev-'プレフィックスが付与されなければならない"
  }

  assert {
    condition     = google_cloud_scheduler_job.scheduler.name == "dev-school-agent-v2-scheduler"
    error_message = "dev環境ではScheduler名に'dev-'プレフィックスが付与されなければならない"
  }

  assert {
    condition     = google_cloud_scheduler_job.scheduler.paused == true
    error_message = "dev環境ではSchedulerがpausedでなければならない"
  }

  assert {
    condition     = data.google_secret_manager_secret.slack_bot_token.secret_id == "dev-school-agent-slack-bot-token"
    error_message = "dev環境ではslack_bot_tokenシークレット名に'dev-'プレフィックスが付与されなければならない"
  }

  assert {
    condition     = data.google_secret_manager_secret.slack_channel_id.secret_id == "dev-school-agent-slack-channel-id"
    error_message = "dev環境ではslack_channel_idシークレット名に'dev-'プレフィックスが付与されなければならない"
  }

  assert {
    condition     = data.google_secret_manager_secret.todoist_api_token.secret_id == "dev-school-agent-todoist-api-token"
    error_message = "dev環境ではtodoist_api_tokenシークレット名に'dev-'プレフィックスが付与されなければならない"
  }
}

# prod: prefix="" でリソース名に接頭辞がなく、scheduler が active になることを検証
run "prod_no_prefix_and_active_scheduler" {
  variables {
    project_id       = "test-project"
    prefix           = ""
    scheduler_paused = false
    env_vars = {
      PROJECT_ID        = "test-project"
      SPREADSHEET_ID    = "dummy-sheet"
      INBOX_FOLDER_ID   = "dummy-inbox"
      ARCHIVE_FOLDER_ID = "dummy-archive"
    }
  }

  command = plan

  assert {
    condition     = google_cloudfunctions2_function.function.name == "school-agent-v2"
    error_message = "prod環境ではFunction名にプレフィックスが付かないこと"
  }

  assert {
    condition     = google_cloud_scheduler_job.scheduler.name == "school-agent-v2-scheduler"
    error_message = "prod環境ではScheduler名にプレフィックスが付かないこと"
  }

  assert {
    condition     = google_cloud_scheduler_job.scheduler.paused == false
    error_message = "prod環境ではSchedulerがactiveでなければならない"
  }

  assert {
    condition     = data.google_secret_manager_secret.slack_bot_token.secret_id == "school-agent-slack-bot-token"
    error_message = "prod環境ではslack_bot_tokenシークレット名にプレフィックスが付かないこと"
  }

  assert {
    condition     = data.google_secret_manager_secret.slack_channel_id.secret_id == "school-agent-slack-channel-id"
    error_message = "prod環境ではslack_channel_idシークレット名にプレフィックスが付かないこと"
  }

  assert {
    condition     = data.google_secret_manager_secret.todoist_api_token.secret_id == "school-agent-todoist-api-token"
    error_message = "prod環境ではtodoist_api_tokenシークレット名にプレフィックスが付かないこと"
  }
}
