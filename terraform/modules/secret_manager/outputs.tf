output "secret_id" {
  description = "Secret Manager のシークレットID（Cloud Run から参照用）"
  value       = google_secret_manager_secret.this.secret_id
}
