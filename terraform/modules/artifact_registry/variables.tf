variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "Artifact Registry のロケーション"
  type        = string
}

variable "repository_id" {
  description = "Artifact Registry リポジトリID"
  type        = string
}

variable "environment" {
  description = "環境名（ラベル用）"
  type        = string
}
