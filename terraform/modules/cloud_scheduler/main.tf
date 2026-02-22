resource "google_cloud_scheduler_job" "this" {
  project   = var.project_id
  region    = var.region
  name      = var.job_name
  schedule  = var.schedule
  time_zone = var.time_zone

  http_target {
    http_method = "POST"
    uri         = var.target_url

    oauth_token {
      service_account_email = var.service_account_email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}
