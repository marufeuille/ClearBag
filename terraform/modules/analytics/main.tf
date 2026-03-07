"""Analytics モジュール - BigQuery + Cloud Logging Sink

Cloud Run stdout → Cloud Logging → Log Sink → BigQuery のパイプラインを構築する。
jsonPayload.log_type フィールドが存在するログのみをキャプチャし、
通常のアプリログは除外される。
"""

resource "google_project_service" "bigquery" {
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "logging" {
  project            = var.project_id
  service            = "logging.googleapis.com"
  disable_on_destroy = false
}

resource "google_bigquery_dataset" "analytics" {
  project    = var.project_id
  dataset_id = "analytics_${var.environment}"
  location   = var.location

  default_table_expiration_ms = var.table_expiration_days > 0 ? var.table_expiration_days * 86400000 : null

  depends_on = [google_project_service.bigquery]
}

resource "google_logging_project_sink" "analytics" {
  project     = var.project_id
  name        = "analytics-to-bigquery-${var.environment}"
  destination = "bigquery.googleapis.com/${google_bigquery_dataset.analytics.id}"

  # log_type フィールドが存在するログのみキャプチャ（access_log + ビジネスイベント）
  # 通常のアプリログ（log_type なし）は除外される
  filter = "resource.type=\"cloud_run_revision\" AND jsonPayload.log_type:*"

  bigquery_options {
    use_partitioned_tables = true
  }

  depends_on = [google_project_service.logging]
}

# Log Sink の書き込み用 SA に BigQuery dataEditor 権限を付与
resource "google_bigquery_dataset_iam_member" "sink_writer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.analytics.writer_identity
}
