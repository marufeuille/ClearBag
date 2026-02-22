variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "github_repo" {
  description = "GitHub リポジトリ名（'owner/repo' 形式）。WIF の attribute_condition に使用し、他リポジトリからの認証を防止する。"
  type        = string
}
