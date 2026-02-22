resource "google_secret_manager_secret" "this" {
  project   = var.project_id
  secret_id = var.secret_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.this.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}
