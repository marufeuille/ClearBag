variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "job_name" {
  description = "監視対象の Cloud Run Job 名"
  type        = string
}

variable "notification_email" {
  description = "アラート通知先メールアドレス"
  type        = string
}
