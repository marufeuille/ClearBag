variable "billing_account_id" {
  description = "GCP 請求先アカウント ID"
  type        = string
  sensitive   = true
}

variable "project_id" {
  description = "予算を監視する GCP プロジェクト ID"
  type        = string
}

variable "budget_amount" {
  description = "月次予算金額 (USD)"
  type        = number
  default     = 50
}

variable "alert_thresholds" {
  description = "アラート通知のしきい値リスト (0.5 = 50%)"
  type        = list(number)
  default     = [0.5, 0.8, 1.0, 1.5]
}

variable "notification_channel_name" {
  description = "Cloud Monitoring 通知チャンネルのリソース名"
  type        = string
}
