output "dataset_id" {
  description = "BigQuery データセット ID"
  value       = google_bigquery_dataset.analytics.dataset_id
}

output "sink_name" {
  description = "Cloud Logging Sink 名"
  value       = google_logging_project_sink.analytics.name
}
