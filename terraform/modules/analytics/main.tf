# Analytics モジュール - BigQuery + Cloud Logging Sink
#
# Cloud Run stdout → Cloud Logging → Log Sink → BigQuery のパイプラインを構築する。
# jsonPayload.log_type フィールドが存在するログのみをキャプチャし、
# 通常のアプリログは除外される。

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

# ---------------------------------------------------------------------------
# BigQuery VIEWs (Phase 2)
#
# Log Sink が自動作成するパーティションテーブルは jsonPayload.* のネスト構造。
# これらの VIEW でフラット化し、Looker Studio から直接クエリできるようにする。
#
# 参照テーブル名: `{project_id}.analytics_{env}.run_googleapis_com_stdout_*`
# ---------------------------------------------------------------------------

locals {
  # 各 VIEW が参照するワイルドカードテーブルのフルパス
  log_table = "`${var.project_id}.analytics_${var.environment}.run_googleapis_com_stdout_*`"
}

# アクセスログフラット化
resource "google_bigquery_table" "v_access_logs" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "v_access_logs"
  deletion_protection = false

  view {
    query          = <<-SQL
      SELECT
        timestamp,
        DATE(timestamp)                        AS date,
        jsonPayload.product_id                 AS product_id,
        jsonPayload.uid                        AS uid,
        jsonPayload.method                     AS method,
        jsonPayload.path                       AS path,
        CAST(jsonPayload.status_code AS INT64) AS status_code,
        CAST(jsonPayload.response_time_ms AS INT64) AS response_time_ms
      FROM ${local.log_table}
      WHERE jsonPayload.log_type = 'access_log'
    SQL
    use_legacy_sql = false
  }

  depends_on = [google_logging_project_sink.analytics]
}

# ドキュメントイベント統合（uploaded / completed / failed / deleted）
resource "google_bigquery_table" "v_document_events" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "v_document_events"
  deletion_protection = false

  view {
    query          = <<-SQL
      SELECT
        timestamp,
        DATE(timestamp)                              AS date,
        jsonPayload.log_type                         AS event_type,
        jsonPayload.product_id                       AS product_id,
        jsonPayload.family_id                        AS family_id,
        jsonPayload.uid                              AS uid,
        jsonPayload.document_id                      AS document_id,
        CAST(jsonPayload.file_size AS INT64)         AS file_size,
        jsonPayload.mime_type                        AS mime_type,
        CAST(jsonPayload.num_pages AS INT64)         AS num_pages,
        jsonPayload.category                         AS category,
        CAST(jsonPayload.events_count AS INT64)      AS events_count,
        CAST(jsonPayload.tasks_count AS INT64)       AS tasks_count,
        CAST(jsonPayload.prompt_tokens AS INT64)     AS prompt_tokens,
        CAST(jsonPayload.candidates_tokens AS INT64) AS candidates_tokens,
        CAST(jsonPayload.total_tokens AS INT64)      AS total_tokens,
        jsonPayload.error                            AS error
      FROM ${local.log_table}
      WHERE jsonPayload.log_type IN (
        'document_uploaded',
        'document_analysis_completed',
        'document_analysis_failed',
        'document_deleted'
      )
    SQL
    use_legacy_sql = false
  }

  depends_on = [google_logging_project_sink.analytics]
}

# DAU / active family 集計（日次）
resource "google_bigquery_table" "v_daily_active_families" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "v_daily_active_families"
  deletion_protection = false

  view {
    query          = <<-SQL
      SELECT
        DATE(timestamp)                      AS date,
        jsonPayload.product_id               AS product_id,
        COUNT(DISTINCT jsonPayload.uid)      AS active_users,
        COUNT(DISTINCT jsonPayload.family_id) AS active_families
      FROM ${local.log_table}
      WHERE jsonPayload.log_type = 'access_log'
        AND jsonPayload.uid IS NOT NULL
      GROUP BY date, product_id
    SQL
    use_legacy_sql = false
  }

  depends_on = [google_logging_project_sink.analytics]
}

# 月次 family 別 Gemini APIコスト集計
resource "google_bigquery_table" "v_monthly_cost_by_family" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "v_monthly_cost_by_family"
  deletion_protection = false

  view {
    query          = <<-SQL
      SELECT
        FORMAT_TIMESTAMP('%Y-%m', timestamp)          AS month,
        jsonPayload.product_id                        AS product_id,
        jsonPayload.family_id                         AS family_id,
        COUNT(*)                                      AS analysis_count,
        SUM(CAST(jsonPayload.total_tokens AS INT64))  AS total_tokens,
        SUM(CAST(jsonPayload.prompt_tokens AS INT64)) AS prompt_tokens,
        SUM(CAST(jsonPayload.candidates_tokens AS INT64)) AS candidates_tokens,
        SUM(CAST(jsonPayload.file_size AS INT64))     AS total_file_size_bytes,
        AVG(CAST(jsonPayload.file_size AS INT64))     AS avg_file_size_bytes
      FROM ${local.log_table}
      WHERE jsonPayload.log_type = 'document_analysis_completed'
      GROUP BY month, product_id, family_id
    SQL
    use_legacy_sql = false
  }

  depends_on = [google_logging_project_sink.analytics]
}
