# ---------------------------------------------------------------------------
# Cloud Monitoring - Cloud Run Job 失敗アラート
# ---------------------------------------------------------------------------

# メール通知チャンネル
resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "Email - ${var.notification_email}"
  type         = "email"

  labels = {
    email_address = var.notification_email
  }
}

# Cloud Run Job 実行失敗アラート（job_name が指定された場合のみ作成）
resource "google_monitoring_alert_policy" "job_failure" {
  count = var.job_name != "" ? 1 : 0

  project      = var.project_id
  display_name = "Cloud Run Job Failure - ${var.job_name}"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run Job failed execution"

    condition_threshold {
      filter = <<-EOT
        resource.type = "cloud_run_job"
        AND resource.labels.job_name = "${var.job_name}"
        AND metric.type = "run.googleapis.com/job/completed_execution_count"
        AND metric.labels.result = "failed"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_COUNT"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email.name,
  ]

  alert_strategy {
    auto_close = "604800s" # 7日後に自動クローズ
  }
}
