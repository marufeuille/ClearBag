output "dataset_id" {
  description = "BigQuery データセット ID"
  value       = google_bigquery_dataset.analytics.dataset_id
}

output "sink_name" {
  description = "Cloud Logging Sink 名"
  value       = google_logging_project_sink.analytics.name
}

output "views" {
  description = "作成した BigQuery VIEW の table_id 一覧"
  value = [
    google_bigquery_table.v_access_logs.table_id,
    google_bigquery_table.v_document_events.table_id,
    google_bigquery_table.v_daily_active_families.table_id,
    google_bigquery_table.v_monthly_cost_by_family.table_id,
  ]
}
