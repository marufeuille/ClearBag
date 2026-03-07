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
# create_views.sh で CREATE OR REPLACE VIEW DDL を実行してフラット化する。
#
# google_bigquery_table の view ブロックではなく bq query DDL を使う理由:
# BigQuery API はワイルドカードテーブルが存在しない状態での VIEW 作成を
# 400 エラーで拒否するため。Log Sink テーブルは最初のログ到着後に自動作成
# されるため、初回デプロイ時は常にテーブルが存在しない。
#
# VIEW の SQL は create_views.sh に記述してコード管理する。
# テーブルが存在しない場合はスクリプト内で警告を出してスキップする。
# ---------------------------------------------------------------------------

resource "terraform_data" "bq_views" {
  # create_views.sh の内容が変わると再実行
  triggers_replace = filesha256("${path.module}/create_views.sh")

  provisioner "local-exec" {
    command = "bash ${path.module}/create_views.sh"
    environment = {
      PROJECT_ID  = var.project_id
      ENVIRONMENT = var.environment
    }
  }

  depends_on = [google_logging_project_sink.analytics]
}
