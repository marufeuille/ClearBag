output "dataset_id" {
  description = "BigQuery データセット ID"
  value       = google_bigquery_dataset.analytics.dataset_id
}

output "sink_name" {
  description = "Cloud Logging Sink 名"
  value       = google_logging_project_sink.analytics.name
}

output "views" {
  description = "作成した BigQuery VIEW の table_id 一覧（create_views.sh で管理）"
  value = [
    "v_access_logs",
    "v_document_events",
    "v_daily_active_families",
    "v_monthly_cost_by_family",
  ]
}
