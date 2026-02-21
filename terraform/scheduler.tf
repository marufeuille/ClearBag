resource "google_cloud_scheduler_job" "scheduler" {
  name        = "${var.function_name}-scheduler"
  description = "School Agent v2 scheduler - runs at 9:00 and 17:00 JST"
  schedule    = var.scheduler_schedule
  time_zone   = var.scheduler_timezone
  region      = var.region
  project     = var.project_id

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.function.service_config[0].uri

    oidc_token {
      service_account_email = local.effective_service_account
    }
  }

  retry_config {
    retry_count          = 0
    min_backoff_duration = "5s"
    max_backoff_duration = "300s"
  }

  depends_on = [google_cloudfunctions2_function.function]
}
