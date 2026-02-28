variable "project_id" {
  description = "prod 環境の GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "デプロイリージョン"
  type        = string
  default     = "asia-northeast1"
}

variable "image_url" {
  description = "デプロイするコンテナイメージ URL（latest-prod タグ固定。cd-prod-terraform.yml から -var で渡す）"
  type        = string
}

variable "spreadsheet_id" {
  description = "Google スプレッドシートID"
  type        = string
}

variable "inbox_folder_id" {
  description = "受信フォルダID（Google Drive）"
  type        = string
}

variable "archive_folder_id" {
  description = "アーカイブフォルダID（Google Drive）"
  type        = string
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
  description = "月次予算金額 (USD)"
  type        = number
  default     = 50
}
