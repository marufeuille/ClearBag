variable "project_id" {
  type        = string
  description = "GCP プロジェクト ID"
}

variable "location" {
  type        = string
  description = "Firestore のロケーション（例: asia-northeast1）"
  default     = "asia-northeast1"
}

variable "service_account_email" {
  type        = string
  description = "Firestore への読み書き権限を付与するサービスアカウント"
}
