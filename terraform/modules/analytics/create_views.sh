#!/usr/bin/env bash
# BigQuery VIEW 作成スクリプト
#
# google_bigquery_table リソースで VIEW を作成しようとすると、
# ワイルドカードテーブル (run_googleapis_com_stdout) が存在しない場合に
# BigQuery API が 400 エラーを返すため、このスクリプトで CREATE OR REPLACE VIEW を
# 直接実行する。テーブルが存在しない場合のエラーは警告として扱いスキップする。
#
# 前提: bq CLI が PATH に存在すること（CI: setup-gcloud で自動セットアップ済み）
# 環境変数: PROJECT_ID, ENVIRONMENT

set -uo pipefail

PROJECT_ID="${PROJECT_ID}"
ENVIRONMENT="${ENVIRONMENT}"
DATASET="analytics_${ENVIRONMENT}"

create_view() {
  local view_id="$1"
  local sql="$2"
  if bq query \
       --use_legacy_sql=false \
       --project_id="${PROJECT_ID}" \
       --quiet \
       "${sql}" 2>&1; then
    echo "BigQuery VIEW ${view_id}: created/updated"
  else
    echo "Warning: BigQuery VIEW ${view_id} skipped (source table may not exist yet)"
  fi
}

# v_access_logs: アクセスログ フラット化
create_view "v_access_logs" "CREATE OR REPLACE VIEW \`${PROJECT_ID}.${DATASET}.v_access_logs\` AS
SELECT
  timestamp,
  DATE(timestamp)                        AS date,
  jsonPayload.product_id                 AS product_id,
  jsonPayload.uid                        AS uid,
  jsonPayload.method                     AS method,
  jsonPayload.path                       AS path,
  CAST(jsonPayload.status_code AS INT64) AS status_code,
  CAST(jsonPayload.response_time_ms AS INT64) AS response_time_ms
FROM \`${PROJECT_ID}.${DATASET}.run_googleapis_com_stdout\`
WHERE jsonPayload.log_type = 'access_log'"

# v_document_events: ドキュメントイベント統合
create_view "v_document_events" "CREATE OR REPLACE VIEW \`${PROJECT_ID}.${DATASET}.v_document_events\` AS
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
  JSON_VALUE(TO_JSON_STRING(jsonPayload), '$.error') AS error
FROM \`${PROJECT_ID}.${DATASET}.run_googleapis_com_stdout\`
WHERE jsonPayload.log_type IN (
  'document_uploaded',
  'document_analysis_completed',
  'document_analysis_failed',
  'document_deleted'
)"

# v_daily_active_families: DAU / active family 集計（日次）
create_view "v_daily_active_families" "CREATE OR REPLACE VIEW \`${PROJECT_ID}.${DATASET}.v_daily_active_families\` AS
SELECT
  DATE(timestamp)                      AS date,
  jsonPayload.product_id               AS product_id,
  COUNT(DISTINCT jsonPayload.uid)      AS active_users,
  COUNT(DISTINCT jsonPayload.family_id) AS active_families
FROM \`${PROJECT_ID}.${DATASET}.run_googleapis_com_stdout\`
WHERE jsonPayload.log_type = 'access_log'
  AND jsonPayload.uid IS NOT NULL
GROUP BY date, product_id"

# v_monthly_cost_by_family: 月次 family 別 Gemini APIコスト集計
create_view "v_monthly_cost_by_family" "CREATE OR REPLACE VIEW \`${PROJECT_ID}.${DATASET}.v_monthly_cost_by_family\` AS
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
FROM \`${PROJECT_ID}.${DATASET}.run_googleapis_com_stdout\`
WHERE jsonPayload.log_type = 'document_analysis_completed'
GROUP BY month, product_id, family_id"
