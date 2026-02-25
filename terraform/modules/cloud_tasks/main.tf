resource "google_cloud_tasks_queue" "this" {
  project  = var.project_id
  location = var.location
  name     = var.queue_name

  rate_limits {
    max_dispatches_per_second  = var.max_dispatches_per_second
    max_concurrent_dispatches  = var.max_concurrent_dispatches
  }

  retry_config {
    max_attempts  = var.max_attempts
    min_backoff   = "10s"
    max_backoff   = "300s"   # 5 分
    max_doublings = 4
  }
}

# Cloud Run SA が Cloud Tasks にタスクを追加できる権限
resource "google_project_iam_member" "tasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${var.service_account_email}"
}
