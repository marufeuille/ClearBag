variable "project_id" {
  description = "dev 環境の GCP プロジェクトID"
  type        = string
}

variable "region" {
  description = "デプロイリージョン"
  type        = string
  default     = "asia-northeast1"
}

variable "image_url" {
  description = "デプロイするコンテナイメージ URL（deploy 時に -var で渡す）"
  type        = string
}

variable "api_image_url" {
  description = "B2C API サーバーのコンテナイメージ URL（deploy 時に -var で渡す）"
  type        = string
  default     = "asia-northeast1-docker.pkg.dev/clearbag-dev/school-agent-dev/school-agent-v2:latest"
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

variable "allowed_emails" {
  description = "ログイン許可メールアドレス（カンマ区切り）。未設定の場合は全員許可。dev環境アクセス制限用"
  type        = string
  default     = ""
}
