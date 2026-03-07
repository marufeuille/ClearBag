variable "project_id" {
  description = "GCP プロジェクト ID"
  type        = string
}

variable "environment" {
  description = "環境名（dev / prod）。BigQuery データセット名のサフィックスに使用する"
  type        = string
}

variable "location" {
  description = "BigQuery データセットのロケーション（例: asia-northeast1）"
  type        = string
}

variable "table_expiration_days" {
  description = "BigQuery テーブルの自動削除までの日数。0 を指定すると期限なし（prod 推奨）"
  type        = number
  default     = 0
}
