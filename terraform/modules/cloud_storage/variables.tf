variable "project_id" {
  type        = string
  description = "GCP プロジェクト ID"
}

variable "bucket_name" {
  type        = string
  description = "GCS バケット名（グローバルで一意）"
}

variable "location" {
  type        = string
  description = "バケットのリージョン"
  default     = "ASIA-NORTHEAST1"
}

variable "service_account_email" {
  type        = string
  description = "バケットへのアクセス権限を付与するサービスアカウント"
}

variable "lifecycle_delete_days" {
  type        = number
  description = "オブジェクトを自動削除するまでの日数（0 = 削除なし）"
  default     = 365
}
