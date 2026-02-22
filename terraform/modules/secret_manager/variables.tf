variable "project_id" {
  description = "GCP プロジェクトID"
  type        = string
}

variable "secret_id" {
  description = "Secret Manager のシークレットID"
  type        = string
}

variable "service_account_email" {
  description = "SecretAccessor 権限を付与するサービスアカウントのメールアドレス"
  type        = string
}
