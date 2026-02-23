resource "google_artifact_registry_repository" "this" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
  description   = "school-agent コンテナイメージリポジトリ (${var.environment})"

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }

  # まず dry_run で動作確認してから false に切り替える
  cleanup_policy_dry_run = true

  cleanup_policies {
    id     = "delete-old-images"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30日
    }
  }

  cleanup_policies {
    id     = "keep-tagged-releases"
    action = "KEEP"
    condition {
      tag_prefixes = ["latest", "latest-prod", "v"]
    }
  }
}
