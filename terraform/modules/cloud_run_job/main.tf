resource "google_cloud_run_v2_job" "this" {
  project  = var.project_id
  name     = var.job_name
  location = var.region

  deletion_protection = false

  template {
    task_count = 1

    template {
      service_account = var.service_account_email != "" ? var.service_account_email : null
      max_retries     = var.max_retries
      timeout         = var.timeout

      containers {
        image   = var.image_url
        command = length(var.command) > 0 ? var.command : null

        resources {
          limits = {
            memory = var.memory
            cpu    = var.cpu
          }
        }

        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = var.secret_env_vars
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.this.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.invoker_service_account_email}"
}
