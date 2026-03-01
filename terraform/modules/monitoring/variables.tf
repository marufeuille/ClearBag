variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "job_name" {
  description = "監視対象の Cloud Run Job 名（空文字列の場合はアラートを作成しない）"
  type        = string
  default     = ""
}

variable "notification_email" {
  description = "アラート通知先メールアドレス"
  type        = string
}
