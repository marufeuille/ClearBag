variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "Cloud Run Job のリージョン"
  type        = string
}

variable "job_name" {
  description = "Cloud Run Job 名"
  type        = string
}

variable "image_url" {
  description = "デプロイするコンテナイメージの URL"
  type        = string
}

variable "service_account_email" {
  description = "Job 実行に使用するサービスアカウント（空の場合はデフォルト Compute SA）"
  type        = string
  default     = ""
}

variable "invoker_service_account_email" {
  description = "Job を起動する権限（roles/run.invoker）を付与するサービスアカウント"
  type        = string
}

variable "memory" {
  description = "コンテナに割り当てるメモリ量"
  type        = string
  default     = "1Gi"
}

variable "cpu" {
  description = "コンテナに割り当てる CPU 数"
  type        = string
  default     = "1"
}

variable "max_retries" {
  description = "タスク失敗時の最大リトライ数（0 = リトライなし）"
  type        = number
  default     = 0
}

variable "timeout" {
  description = "タスクのタイムアウト（例: 3600s = 1時間）"
  type        = string
  default     = "3600s"
}

variable "env_vars" {
  description = "通常の環境変数マッピング（key: 環境変数名, value: 値）"
  type        = map(string)
  default     = {}
}

variable "secret_env_vars" {
  description = "Secret Manager から注入する環境変数マッピング（key: 環境変数名, value: Secret ID）"
  type        = map(string)
  default     = {}
}
