output "notification_channel_name" {
  value       = google_monitoring_notification_channel.email.name
  description = "メール通知チャンネルのリソース名"
}
