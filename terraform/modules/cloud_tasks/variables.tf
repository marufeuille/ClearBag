variable "project_id" {
  type        = string
  description = "GCP プロジェクト ID"
}

variable "location" {
  type        = string
  description = "Cloud Tasks のリージョン"
  default     = "asia-northeast1"
}

variable "queue_name" {
  type        = string
  description = "Cloud Tasks キュー名"
}

variable "service_account_email" {
  type        = string
  description = "Cloud Tasks タスクを作成する SA に付与する権限"
}

variable "max_dispatches_per_second" {
  type        = number
  description = "1 秒あたりの最大ディスパッチ数（Gemini API のレート制限に合わせる）"
  default     = 1
}

variable "max_concurrent_dispatches" {
  type        = number
  description = "同時実行の最大数"
  default     = 5
}

variable "max_attempts" {
  type        = number
  description = "最大リトライ回数（-1 = 無制限）"
  default     = 5
}
