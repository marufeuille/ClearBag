# Looker Studio ダッシュボード用 SQL クエリ集

BigQuery に作成済みの VIEW を Looker Studio のデータソースとして使うためのクエリ集。
Looker Studio はコード管理できないため、各チャート用の SQL をここで管理する。

---

## 利用可能な VIEW

| VIEW | 主なカラム |
|------|-----------|
| `v_access_logs` | date, uid, method, path, status_code, response_time_ms |
| `v_document_events` | date, event_type, family_id, uid, document_id, file_size, prompt_tokens, candidates_tokens, total_tokens |
| `v_daily_active_families` | date, active_users, active_families |
| `v_monthly_cost_by_family` | month, family_id, analysis_count, total_tokens, prompt_tokens, candidates_tokens |

## Gemini 2.5 Pro 料金（2026年3月時点の概算）

| 項目 | 単価 |
|------|------|
| Input tokens (≤200K context) | $1.25 / 1M tokens |
| Output tokens (≤200K context) | $10.00 / 1M tokens |

料金改定時は各 SQL 内の `1.25` / `10.0` を更新すること。

---

## クエリ一覧

### 1. DAU（日次アクティブユーザー数）

`v_daily_active_families` VIEW をそのまま Looker Studio のデータソースに接続してもよい。
カスタムクエリを使う場合：

```sql
SELECT
  date,
  active_users,
  active_families
FROM `<PROJECT_ID>.analytics_<ENV>.v_daily_active_families`
WHERE date BETWEEN PARSE_DATE('%Y%m%d', @DS_START_DATE) AND PARSE_DATE('%Y%m%d', @DS_END_DATE)
ORDER BY date
```

**チャート**: 折れ線グラフ（X: date, Y: active_users / active_families）

---

### 2. 各 family_id ごとの処理枚数 / day

```sql
SELECT
  date,
  family_id,
  COUNT(DISTINCT document_id) AS documents_processed
FROM `<PROJECT_ID>.analytics_<ENV>.v_document_events`
WHERE event_type = 'document_analysis_completed'
  AND date BETWEEN PARSE_DATE('%Y%m%d', @DS_START_DATE) AND PARSE_DATE('%Y%m%d', @DS_END_DATE)
GROUP BY date, family_id
ORDER BY date, family_id
```

**チャート**: 積み上げ棒グラフ（X: date, 色分け: family_id, Y: documents_processed）

---

### 3. 各 family_id ごとの API 課金額 / day

```sql
SELECT
  date,
  family_id,
  COUNT(DISTINCT document_id)  AS analysis_count,
  SUM(prompt_tokens)           AS total_prompt_tokens,
  SUM(candidates_tokens)       AS total_candidates_tokens,
  SUM(total_tokens)            AS total_all_tokens,
  -- Gemini 2.5 Pro 料金概算 (USD)
  ROUND(
    SUM(prompt_tokens)      / 1000000.0 * 1.25
  + SUM(candidates_tokens)  / 1000000.0 * 10.0
  , 4) AS estimated_cost_usd
FROM `<PROJECT_ID>.analytics_<ENV>.v_document_events`
WHERE event_type = 'document_analysis_completed'
  AND date BETWEEN PARSE_DATE('%Y%m%d', @DS_START_DATE) AND PARSE_DATE('%Y%m%d', @DS_END_DATE)
GROUP BY date, family_id
ORDER BY date, family_id
```

**チャート**:
- 積み上げ棒グラフ（X: date, 色分け: family_id, Y: estimated_cost_usd）
- スコアカード: 期間合計コスト

---

### 4. 処理ファイル数 / day（全体）

```sql
SELECT
  date,
  COUNT(DISTINCT document_id)                                                         AS files_processed,
  COUNT(DISTINCT CASE WHEN event_type = 'document_uploaded'           THEN document_id END) AS files_uploaded,
  COUNT(DISTINCT CASE WHEN event_type = 'document_analysis_completed' THEN document_id END) AS files_completed,
  COUNT(DISTINCT CASE WHEN event_type = 'document_analysis_failed'    THEN document_id END) AS files_failed
FROM `<PROJECT_ID>.analytics_<ENV>.v_document_events`
WHERE event_type IN ('document_uploaded', 'document_analysis_completed', 'document_analysis_failed')
  AND date BETWEEN PARSE_DATE('%Y%m%d', @DS_START_DATE) AND PARSE_DATE('%Y%m%d', @DS_END_DATE)
GROUP BY date
ORDER BY date
```

**チャート**:
- 折れ線グラフ（X: date, Y: files_uploaded / files_completed / files_failed）
- 成功率スコアカード: `files_completed / files_uploaded * 100`

---

### 5. ファイルごとの API 課金額 / day（平均・Max・Min）

```sql
WITH per_file AS (
  SELECT
    date,
    document_id,
    prompt_tokens,
    candidates_tokens,
    total_tokens,
    ROUND(
      prompt_tokens      / 1000000.0 * 1.25
    + candidates_tokens  / 1000000.0 * 10.0
    , 6) AS cost_usd
  FROM `<PROJECT_ID>.analytics_<ENV>.v_document_events`
  WHERE event_type = 'document_analysis_completed'
    AND date BETWEEN PARSE_DATE('%Y%m%d', @DS_START_DATE) AND PARSE_DATE('%Y%m%d', @DS_END_DATE)
)
SELECT
  date,
  COUNT(*)                     AS file_count,
  ROUND(AVG(cost_usd), 6)     AS avg_cost_usd,
  ROUND(MAX(cost_usd), 6)     AS max_cost_usd,
  ROUND(MIN(cost_usd), 6)     AS min_cost_usd,
  ROUND(SUM(cost_usd), 4)     AS total_cost_usd,
  -- トークン統計も参考に
  ROUND(AVG(total_tokens), 0)  AS avg_tokens,
  MAX(total_tokens)             AS max_tokens,
  MIN(total_tokens)             AS min_tokens
FROM per_file
GROUP BY date
ORDER BY date
```

**チャート**:
- 折れ線グラフ（X: date, Y: avg_cost_usd, max_cost_usd, min_cost_usd）
- テーブル: 日別の詳細統計

---

## Looker Studio 構成メモ

- **データソース**: BigQuery カスタムクエリ（上記5つ）
- **日付フィルタ**: Looker Studio の「期間コントロール」ウィジェットで `@DS_START_DATE` / `@DS_END_DATE` を自動バインド（値は `YYYYMMDD` 形式の文字列）
- **`<PROJECT_ID>` / `<ENV>`**: データソース作成時に実際の値（例: `clearbag-dev` / `dev`）に置換すること
- **料金単価の変更**: Gemini の料金改定時は SQL 内の `1.25` / `10.0` を更新

---

## 検証方法

BigQuery コンソールで各 SQL を実行して結果が返ることを確認する。
`@DS_START_DATE` / `@DS_END_DATE` は手動テスト時に以下で代替：

```sql
-- @DS_START_DATE の代替（YYYYMMDD 文字列 → DATE に変換）
PARSE_DATE('%Y%m%d', FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)))
-- または単純に
DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)

-- @DS_END_DATE の代替
PARSE_DATE('%Y%m%d', FORMAT_DATE('%Y%m%d', CURRENT_DATE()))
-- または単純に
CURRENT_DATE()
```

> 注意: `@DS_START_DATE` / `@DS_END_DATE` は Looker Studio が `YYYYMMDD` 形式の文字列として渡す。
> クエリ内では `PARSE_DATE('%Y%m%d', @DS_START_DATE)` で DATE 型に変換してから比較すること。

Looker Studio でデータソースを作成し、チャートが描画されることを確認する。
