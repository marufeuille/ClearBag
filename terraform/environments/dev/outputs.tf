output "registry_url" {
  description = "dev 環境の Artifact Registry URL"
  value       = module.artifact_registry.registry_url
}

output "image_base" {
  description = "dev 環境のイメージ名ベース"
  value       = module.artifact_registry.image_base
}

output "job_name" {
  description = "dev 環境の Cloud Run Job 名"
  value       = module.cloud_run_job.job_name
}

output "service_account_email" {
  description = "dev 環境の Cloud Run 実行 SA メールアドレス"
  value       = google_service_account.cloud_run.email
}
