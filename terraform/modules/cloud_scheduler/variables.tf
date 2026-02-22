variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "Cloud Scheduler のロケーション"
  type        = string
}

variable "job_name" {
  description = "Cloud Scheduler ジョブ名"
  type        = string
}

variable "schedule" {
  description = "cron 形式のスケジュール"
  type        = string
}

variable "time_zone" {
  description = "スケジュールのタイムゾーン"
  type        = string
  default     = "Asia/Tokyo"
}

variable "target_url" {
  description = "呼び出す Cloud Run サービスの URL"
  type        = string
}

variable "service_account_email" {
  description = "OIDC トークン生成に使用するサービスアカウント"
  type        = string
}

variable "oidc_audience" {
  description = "OIDC トークンの audience（Cloud Run Jobs の場合は https://run.googleapis.com/）"
  type        = string
  default     = ""
}
