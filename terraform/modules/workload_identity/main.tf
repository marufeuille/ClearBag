data "google_project" "project" {
  project_id = var.project_id
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = var.pool_id
  display_name              = "GitHub Actions"
  description               = "GitHub Actions OIDC 認証用 Workload Identity Pool"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"
  description                        = "GitHub Actions OIDC プロバイダー"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "assertion.repository == '${var.github_repo}' && (${var.ref_condition} || assertion.event_name == 'pull_request')"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
    # google-github-actions/auth@v2 は GitHub OIDC トークンの aud を
    # https://iam.googleapis.com/{provider_path} 形式で送るため、それに合わせる
    allowed_audiences = [
      "https://iam.googleapis.com/projects/${data.google_project.project.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/providers/github-oidc"
    ]
  }
}

resource "google_service_account" "github_actions" {
  project      = var.project_id
  account_id   = var.sa_account_id
  display_name = "GitHub Actions デプロイ用 SA"
  description  = "GitHub Actions から GCP リソースを操作するためのサービスアカウント"
}

resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
