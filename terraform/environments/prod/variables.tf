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
