resource "google_cloud_scheduler_job" "this" {
  project   = var.project_id
  region    = var.region
  name      = var.job_name
  schedule  = var.schedule
  time_zone = var.time_zone

  http_target {
    http_method = "POST"
    uri         = var.target_url

    oidc_token {
      service_account_email = var.service_account_email
      audience              = var.oidc_audience != "" ? var.oidc_audience : var.target_url
    }
  }
}
