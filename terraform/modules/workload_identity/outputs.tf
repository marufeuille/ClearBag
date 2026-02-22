output "workload_identity_provider" {
  description = "WIF Provider のフルパス。GitHub Actions の workload_identity_provider シークレットに設定する。"
  value       = "projects/${data.google_project.project.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id}"
}

output "service_account_email" {
  description = "デプロイ用 SA のメールアドレス。GitHub Actions の service_account シークレットに設定する。"
  value       = google_service_account.github_actions.email
}
