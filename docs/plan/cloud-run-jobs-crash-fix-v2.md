# Cloud Run Jobs「Application exec likely failed」修正プラン v2

## 背景

前回の修正（`v2/adapters/credentials.py` で `CLOUD_RUN_JOB` 環境変数チェックを追加）後も、
Cloud Run Jobs で「Application exec likely failed」が解消しない。

---

## 根本原因の候補（優先度順）

### 原因 A: 修正コードが未デプロイ【最優先確認】

**症状**: コードは修正済みだが Docker イメージが古いまま。

**確認コマンド**:
```bash
# Cloud Run Job が現在使用しているイメージを確認
gcloud run jobs describe school-agent-v2-dev \
  --region=asia-northeast1 \
  --format="value(template.template.containers[0].image)"

# 最新イメージのダイジェストを確認（2つが一致すれば最新）
gcloud artifacts docker images describe \
  asia-northeast1-docker.pkg.dev/${PROJECT_ID}/school-agent-dev/school-agent-v2:latest \
  --format="value(image_summary.digest)"
```

**解決**: `./deploy_dev.sh` を実行してリビルド＋デプロイ。

---

### 原因 B: Secret Manager のシークレットにバージョン（値）が未登録【最有力】

**メカニズム**:

```
terraform/modules/secret_manager/main.tf
  └─ google_secret_manager_secret    ← "器"のみ作成
                                      ← google_secret_manager_secret_version は存在しない

terraform/environments/dev/main.tf（cloud_run_job モジュール）
  └─ secret_env_vars:
       SLACK_BOT_TOKEN   → version = "latest"  ← バージョンがなければコンテナ起動失敗
       SLACK_CHANNEL_ID  → version = "latest"
       TODOIST_API_TOKEN → version = "latest"
```

Cloud Run は Secret Manager シークレットの注入をコンテナ起動 **前** に行う。
バージョンが 1 つも存在しないシークレットを参照していると、
Python すら起動せずに「Application exec likely failed」となる。

**確認コマンド**:
```bash
gcloud secrets versions list school-agent-slack-bot-token-dev
gcloud secrets versions list school-agent-slack-channel-id-dev
gcloud secrets versions list school-agent-todoist-api-token-dev
```

バージョンが 0 件なら、これが原因。

---

### 原因 C: サービスアカウントの IAM 権限不足【起動後エラー】

現在 Terraform で付与されている権限:
- `roles/secretmanager.secretAccessor`（secret_manager モジュールで付与）
- `roles/run.invoker`（cloud_run_job モジュールで付与）

**不足している可能性のある権限**:

| 必要な権限 | 用途 |
|---|---|
| `roles/aiplatform.user` | Vertex AI / Gemini API 呼び出し |
| `roles/iam.serviceAccountTokenCreator` | ADC でのトークン自己発行（場合により必要） |

> **注意**: Google Workspace API（Drive / Sheets / Calendar）は
> ユーザーデータへのアクセスに「ドメイン全体の委任（Domain-wide delegation）」が必要。
> これは IAM ロールではなく Google Workspace Admin Console で設定する別作業であり、
> 本プランのスコープ外とする。

**この原因は起動後の実行時 HTTP 403 エラーとして現れる**ため、
「Application exec likely failed」とは直接関係しないが、
原因 A・B を解消した後に露出する可能性がある。

---

## 修正内容

### 修正 1: Secret Manager へのバージョン登録スクリプトの追加

#### 仕様（ふるまい）

| 項目 | 内容 |
|---|---|
| スクリプト名 | `scripts/register_secrets.sh` |
| 入力 | `.env` ファイルの `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `TODOIST_API_TOKEN` |
| 処理 | 各シークレットに対し、`ENABLED` バージョンが存在しない場合のみ値を登録する |
| 冪等性 | 既存バージョンがある場合は上書きせずスキップ |
| 空値の扱い | 環境変数が未設定の場合、ダミー値 `__empty__` を登録して Cloud Run の起動失敗を防ぐ |
| 出力 | 各シークレットの処理結果（登録 / スキップ / エラー）をログ出力 |

```bash
# 期待される動作イメージ
./scripts/register_secrets.sh
# → [SKIP] school-agent-slack-bot-token-dev: already has a version
# → [OK]   school-agent-slack-channel-id-dev: registered new version
# → [OK]   school-agent-todoist-api-token-dev: registered new version (empty value)
```

#### テスト観点
- バージョン未登録のシークレットに対して `gcloud secrets versions list` でバージョンが作成されること
- バージョン登録済みのシークレットを再実行しても上書きされないこと
- スクリプト実行後に `gcloud run jobs execute school-agent-v2-dev` が起動することを確認

---

### 修正 2: Terraform で IAM ロールを追加（Vertex AI 権限）

#### 仕様（ふるまい）

`terraform/environments/dev/main.tf` に以下を追加:

```hcl
# Vertex AI / Gemini へのアクセス権限
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}
```

| 項目 | 内容 |
|---|---|
| 対象リソース | `google_project_iam_member` |
| 付与ロール | `roles/aiplatform.user` |
| 対象メンバー | `google_service_account.cloud_run.email` |

#### テスト観点
- `terraform plan` で `google_project_iam_member` の追加が差分として表示されること
- `terraform apply` 後、ジョブ実行時に Vertex AI 呼び出しが HTTP 403 にならないこと

---

### 修正 3: cli.py に起動時の環境診断ログを追加

#### 仕様（ふるまい）

`v2/entrypoints/cli.py` の `setup_logging()` 呼び出し直後に環境情報をログ出力する。

| ログ出力タイミング | `main()` 関数の冒頭、`create_orchestrator()` 呼び出し前 |
|---|---|
| ログ内容 | Python バージョン、検出された Cloud 環境変数、認証モード |
| ログレベル | `INFO` |
| マスキング | 値は出力せず、存在有無（`set` / `not set`）のみを出力 |

```
期待されるログ出力例（Cloud Run Jobs 実行時）:
  INFO: [ENV] CLOUD_RUN_JOB=set (school-agent-v2-dev)
  INFO: [ENV] K_SERVICE=not set
  INFO: [AUTH] mode=cloud_adc
```

```
期待されるログ出力例（ローカル実行時）:
  INFO: [ENV] CLOUD_RUN_JOB=not set
  INFO: [ENV] K_SERVICE=not set
  INFO: [AUTH] mode=local
```

#### テスト観点
- Cloud Run Jobs 実行後、Cloud Logging に `[ENV] CLOUD_RUN_JOB=set` が出力されること
- `[AUTH] mode=cloud_adc` が出力され、認証パスが正しく分岐していることを確認できること

---

## 対象ファイル

| ファイル | 変更種別 | 対応する原因 |
|---|---|---|
| `scripts/register_secrets.sh` | 新規作成 | 原因 B |
| `terraform/environments/dev/main.tf` | 修正 | 原因 C |
| `v2/entrypoints/cli.py` | 修正 | デバッグ容易性向上 |

---

## 診断フロー（修正着手前に必ず実施）

```
Step 1: ./deploy_dev.sh を実行（最新コードを必ずデプロイ）
        ↓ まだ失敗する場合
Step 2: gcloud secrets versions list で各シークレットのバージョン確認
        ↓ バージョン 0 件の場合
Step 3: ./scripts/register_secrets.sh を実行して値を登録
        ↓ まだ失敗する場合
Step 4: Cloud Logging で「School Agent v2 - Starting」が出力されているか確認
        ↓ Python ログが出ていない → コンテナ起動前に失敗 → IAM / Secret の問題
        ↓ Python ログが出ている   → コード実行時エラー → ログの詳細で原因特定
```

---

## 検証方法

1. `gcloud run jobs execute school-agent-v2-dev --region=asia-northeast1` でジョブを手動実行
2. Cloud Logging（ログエクスプローラ）で `resource.type="cloud_run_job"` を絞り込み、以下を確認:
   - `[ENV] CLOUD_RUN_JOB=set` が出力される（Python 起動・認証分岐 確認）
   - `[AUTH] mode=cloud_adc` が出力される（ADC パスを使用している確認）
   - エラーなく `"Processing Complete"` が出力される（正常終了確認）
