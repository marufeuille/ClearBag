# アクティブユーザー計測基盤 — 全体設計

作成日: 2026-03-07

## 背景・目的

ClearBag の利用者が増え始めたため、プロダクトの利用状況を計測・可視化する基盤を構築する。
BigQuery を中心としたシンプルなアーキテクチャで、将来のマルチプロダクト展開にも対応する。

### 計測したいメトリクス

| メトリクス | 用途 |
|---|---|
| DAU / MAU (family 単位) | アクティブ利用状況 |
| ファイル送信数 (family 別) | 利用量トレンド |
| API コスト (Gemini トークン数 × ファイルサイズ) | コスト管理 |
| 解析成功率 / エラー率 | 品質モニタリング |
| カテゴリ別解析結果分布 | 文書傾向分析 |
| レスポンスタイム分布 | パフォーマンス監視 |

---

## フェーズ分割

| フェーズ | スコープ | 状態 |
|---|---|---|
| **Phase 1** | ログ出力 + Cloud Logging Sink + BigQuery ロード | **実装済み (2026-03-07)** |
| **Phase 2** | BigQuery VIEW 定義（フラット化・集計用） | 将来 |
| **Phase 3** | Looker Studio ダッシュボード | 将来 |
| **Phase 4** | アラート・異常検知 | 将来 |

---

## アーキテクチャ全体図（Phase 1）

```
[FastAPI on Cloud Run]
  ├─ Access Log Middleware → stdout (全APIリクエスト)
  └─ Business Event Log   → stdout (アップロード・解析完了等)
       ↓ (Cloud Run が自動転送)
[Cloud Logging]
       ↓ (Log Sink: jsonPayload.log_type:*)
[BigQuery: analytics_dev / analytics_prod]
       ↓ (将来 Phase 2)
[BigQuery VIEW] → [Looker Studio] → [アラート]
```

ログフィルタ `jsonPayload.log_type:*` により、`log_type` フィールドを持つ
分析イベントログのみが BigQuery に流れ、通常のアプリログは除外される。

---

## イベントスキーマ一覧

### access_log（全 API リクエスト）

| フィールド | 型 | 説明 |
|---|---|---|
| log_type | string | `"access_log"` |
| product_id | string | `"clearbag"` |
| uid | string/null | Firebase Auth UID（未認証の場合 null） |
| method | string | HTTP メソッド（GET / POST 等） |
| path | string | リクエストパス |
| status_code | int | レスポンスステータス |
| response_time_ms | int | レスポンスタイム(ms) |

### document_uploaded

| フィールド | 型 | 説明 |
|---|---|---|
| log_type | string | `"document_uploaded"` |
| product_id | string | `"clearbag"` |
| family_id | string | ファミリーID |
| uid | string | アップロードユーザー |
| document_id | string | ドキュメントID |
| file_size | int | バイト数 |
| mime_type | string | MIME タイプ |
| num_pages | int/null | PDF ページ数（PDF 以外は null） |

### document_analysis_completed

| フィールド | 型 | 説明 |
|---|---|---|
| log_type | string | `"document_analysis_completed"` |
| product_id | string | `"clearbag"` |
| family_id | string | ファミリーID |
| uid | string | ユーザー |
| document_id | string | ドキュメントID |
| file_size | int | バイト数 |
| mime_type | string | MIME タイプ |
| category | string | 解析カテゴリ（EVENT / TASK / INFO / IGNORE） |
| events_count | int | 抽出イベント数 |
| tasks_count | int | 抽出タスク数 |
| prompt_tokens | int/null | Gemini 入力トークン数 |
| candidates_tokens | int/null | Gemini 出力トークン数 |
| total_tokens | int/null | Gemini 合計トークン数 |

### document_analysis_failed

| フィールド | 型 | 説明 |
|---|---|---|
| log_type | string | `"document_analysis_failed"` |
| product_id | string | `"clearbag"` |
| family_id | string | ファミリーID |
| uid | string | ユーザー |
| document_id | string | ドキュメントID |
| error | string | エラーメッセージ |

### document_deleted

| フィールド | 型 | 説明 |
|---|---|---|
| log_type | string | `"document_deleted"` |
| product_id | string | `"clearbag"` |
| family_id | string | ファミリーID |
| uid | string | ユーザー |
| document_id | string | ドキュメントID |

---

## Phase 1 実装詳細

### ログユーティリティ (`v2/analytics.py`)

```python
def log_event(log_type: str, **fields) -> None:
    _logger.info(
        log_type,
        extra={"extra_fields": {"log_type": log_type, "product_id": _PRODUCT_ID, **fields}},
    )
```

`CloudLoggingFormatter`（`v2/logging_config.py`）の `extra_fields` 機構を活用し、
jsonPayload に構造化フィールドをフラットに展開する。

### ドメインモデル拡張 (`v2/domain/models.py`)

```python
@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    candidates_tokens: int = 0
    total_tokens: int = 0

@dataclass(frozen=True)
class AnalysisResult:
    analysis: DocumentAnalysis   # ドメインモデルをインフラ情報で汚さない
    token_usage: TokenUsage | None = None
```

### Terraform モジュール (`terraform/modules/analytics/`)

- BigQuery データセット: `analytics_{env}`
- Cloud Logging Sink: `analytics-to-bigquery-{env}`
- パーティションテーブル有効（日次コストの可視化）
- dev: テーブル有効期限 90 日 / prod: 無期限

---

## Phase 2: BigQuery VIEW 定義（将来実装）

Cloud Logging Sink が作成するテーブルは `jsonPayload.*` ネスト構造のため、
分析しやすいフラット VIEW を定義する。

```sql
-- アクセスログフラット化
CREATE OR REPLACE VIEW analytics_dev.v_access_logs AS
SELECT
  timestamp, DATE(timestamp) AS date,
  jsonPayload.uid AS uid, jsonPayload.path AS path,
  jsonPayload.status_code AS status_code,
  jsonPayload.response_time_ms AS response_time_ms
FROM `clearbag-dev.analytics_dev.run_googleapis_com_stdout_*`
WHERE jsonPayload.log_type = 'access_log';

-- DAU 集計
CREATE OR REPLACE VIEW analytics_dev.v_daily_active_families AS
SELECT
  DATE(timestamp) AS date, jsonPayload.product_id AS product_id,
  COUNT(DISTINCT jsonPayload.uid) AS active_users,
  COUNT(DISTINCT jsonPayload.family_id) AS active_families
FROM `clearbag-dev.analytics_dev.run_googleapis_com_stdout_*`
WHERE jsonPayload.log_type = 'access_log' AND jsonPayload.uid IS NOT NULL
GROUP BY date, product_id;

-- 月次 family 別コスト
CREATE OR REPLACE VIEW analytics_dev.v_monthly_cost_by_family AS
SELECT
  FORMAT_TIMESTAMP('%Y-%m', timestamp) AS month,
  jsonPayload.family_id AS family_id,
  COUNT(*) AS analysis_count,
  SUM(CAST(jsonPayload.total_tokens AS INT64)) AS total_tokens,
  SUM(CAST(jsonPayload.file_size AS INT64)) AS total_file_size_bytes
FROM `clearbag-dev.analytics_dev.run_googleapis_com_stdout_*`
WHERE jsonPayload.log_type = 'document_analysis_completed'
GROUP BY month, family_id;
```

---

## Phase 3: Looker Studio ダッシュボード（将来実装）

BigQuery VIEW を直接データソースとして接続（無料）。

| ページ | 主要パネル |
|---|---|
| ユーザーアクティビティ | DAU/MAU 折れ線、エンドポイント別リクエスト、レスポンスタイム分布 |
| ドキュメント解析 | 日次アップロード数、解析成功率（completed vs failed）、カテゴリ分布 |
| API コスト | 月次トークン消費推移、family 別コスト、ファイルサイズ × トークン散布図 |

フィルタコントロール: `product_id`（マルチプロダクト切替）、日付範囲

---

## Phase 4: アラート・異常検知（将来実装）

Cloud Monitoring ログベースメトリクスでシンプルに実装する。

| アラート | 条件 |
|---|---|
| 解析失敗率上昇 | `document_analysis_failed` が 1 時間に 3 件以上 |
| API コスト急増 | 日次トークン消費量が前日の 5 倍以上 |
| 応答遅延 | `response_time_ms` P95 が 5000ms 超 |

---

## BigQuery クエリ例

```sql
-- DAU (family 単位)
SELECT DATE(timestamp) AS date, COUNT(DISTINCT jsonPayload.uid) AS dau
FROM `clearbag-dev.analytics_dev.run_googleapis_com_stdout_*`
WHERE jsonPayload.log_type = 'access_log' AND jsonPayload.uid IS NOT NULL
GROUP BY date ORDER BY date;

-- family 別ファイル送信数
SELECT jsonPayload.family_id, COUNT(*) AS uploads
FROM `clearbag-dev.analytics_dev.run_googleapis_com_stdout_*`
WHERE jsonPayload.log_type = 'document_uploaded'
GROUP BY 1 ORDER BY uploads DESC;

-- ドキュメント単位のトークンコスト
SELECT jsonPayload.family_id, jsonPayload.document_id,
       jsonPayload.file_size, jsonPayload.total_tokens
FROM `clearbag-dev.analytics_dev.run_googleapis_com_stdout_*`
WHERE jsonPayload.log_type = 'document_analysis_completed'
ORDER BY timestamp DESC;
```

---

## コスト見積もり

ユーザー 1-2 人: 全て無料枠内で $0/月。
ユーザー 100 人でも $1 未満。

---

## マルチプロダクト拡張パス

`product_id` カラムで区別する設計のため、別プロダクト追加は以下のみ：

1. 別プロダクトアプリに `log_event()` 相当を実装（`PRODUCT_ID` 環境変数を変える）
2. 同一 GCP プロジェクトなら同じ Log Sink で自動キャプチャ
3. Looker Studio の `product_id` フィルタで切り替え

---

## prod 展開（Phase 1 後続）

`terraform/environments/prod/main.tf` に analytics モジュールを追加:

```hcl
module "analytics" {
  source                = "../../modules/analytics"
  project_id            = var.project_id
  environment           = "prod"
  location              = var.region
  table_expiration_days = 0  # prod は無期限保持
  depends_on            = [google_project_iam_member.github_actions]
}
```

また `locals.github_actions_roles` に以下を追加:
- `"roles/bigquery.admin"`
- `"roles/logging.configWriter"`

Cloud Run の `env_vars` に `PRODUCT_ID = "clearbag"` を追加。
