variable "project_id" {
  type        = string
  description = "GCP プロジェクト ID"
}

variable "region" {
  type        = string
  description = "Cloud Run のリージョン"
}

variable "service_name" {
  type        = string
  description = "Cloud Run Service 名"
}

variable "image_url" {
  type        = string
  description = "デプロイする Docker イメージ URL"
}

variable "service_account_email" {
  type        = string
  description = "Cloud Run Service が使用するサービスアカウントのメールアドレス"
}

variable "env_vars" {
  type        = map(string)
  description = "環境変数のマップ"
  default     = {}
}

variable "secret_env_vars" {
  type        = map(string)
  description = "Secret Manager から注入する環境変数のマップ（key: 環境変数名, value: Secret ID）"
  default     = {}
}

variable "min_instances" {
  type        = number
  description = "最小インスタンス数（コールドスタート軽減用）"
  default     = 0
}

variable "max_instances" {
  type        = number
  description = "最大インスタンス数"
  default     = 10
}

variable "memory" {
  type        = string
  description = "メモリ上限"
  default     = "512Mi"
}

variable "cpu" {
  type        = string
  description = "CPU 上限"
  default     = "1"
}

variable "concurrency" {
  type        = number
  description = "1 インスタンスが同時に処理するリクエスト数"
  default     = 80
}

variable "allow_unauthenticated" {
  type        = bool
  description = "認証なしのアクセスを許可するか（Firebase Auth で保護する場合は true）"
  default     = true
}
