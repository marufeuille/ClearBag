output "registry_url" {
  description = "prod 環境の Artifact Registry URL"
  value       = module.artifact_registry.registry_url
}

output "image_base" {
  description = "prod 環境のイメージ名ベース"
  value       = module.artifact_registry.image_base
}

output "service_account_email" {
  description = "prod 環境の Cloud Run 実行 SA メールアドレス"
  value       = google_service_account.cloud_run.email
}

output "workload_identity_provider" {
  description = "GitHub Actions WIF Provider のフルパス（GitHub Environment Secret: WIF_PROVIDER に設定）"
  value       = module.workload_identity.workload_identity_provider
}

output "github_actions_service_account_email" {
  description = "GitHub Actions prod デプロイ用 SA メールアドレス（GitHub Environment Secret: WIF_SERVICE_ACCOUNT に設定）"
  value       = module.workload_identity.service_account_email
}
