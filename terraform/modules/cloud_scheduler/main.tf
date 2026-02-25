resource "google_cloud_scheduler_job" "this" {
  project   = var.project_id
  region    = var.region
  name      = var.job_name
  schedule  = var.schedule
  time_zone = var.time_zone

  http_target {
    http_method = "POST"
    uri         = var.target_url

    dynamic "oauth_token" {
      for_each = var.use_oidc ? [] : [1]
      content {
        service_account_email = var.service_account_email
        scope                 = "https://www.googleapis.com/auth/cloud-platform"
      }
    }

    dynamic "oidc_token" {
      for_each = var.use_oidc ? [1] : []
      content {
        service_account_email = var.service_account_email
        audience              = var.target_url
      }
    }
  }
}
