variable "project_id" {
  description = "prod 環境の GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "デプロイリージョン"
  type        = string
  default     = "asia-northeast1"
}

variable "notification_email" {
  description = "Cloud Monitoring アラート通知先メールアドレス"
  type        = string
}

variable "billing_account_id" {
  description = "GCP 請求先アカウント ID（GitHub Secrets の TF_VAR_BILLING_ACCOUNT_ID から渡す）"
  type        = string
  sensitive   = true
}

variable "budget_amount" {
  description = "月次予算金額（currency_code で指定した通貨建て）"
  type        = number
  default     = 50
}

variable "currency_code" {
  description = "予算通貨コード（請求アカウントの通貨と一致させること。例: JPY, USD）"
  type        = string
  default     = "JPY"
}
