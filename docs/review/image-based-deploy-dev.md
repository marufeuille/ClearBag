# レビューレポート: image-based-deploy-dev

**日付**: 2026-02-22
**レビュアー**: /reviewer skill
**仕様書**: `docs/plan/image-based-deploy-dev.md` (v4)

---

## 全体ステータス

**✅ PASS**

---

## 要件カバレッジ

### terraform/modules/cloud_run_job（新規作成）

| チェック項目 | 結果 |
|---|---|
| `terraform/modules/cloud_run_job/variables.tf` が新規作成されている | ✅ |
| `terraform/modules/cloud_run_job/main.tf` が新規作成されている | ✅ |
| `terraform/modules/cloud_run_job/outputs.tf` が新規作成されている | ✅ |
| `google_cloud_run_v2_job` リソースが `template.template` のネスト構造で定義されている | ✅ |
| `deletion_protection = false` が設定されている | ✅ |
| `task_count = 1` が設定されている | ✅ |
| `max_retries` / `timeout` が設定されている | ✅ |
| `env_vars` の `dynamic "env"` ブロックが実装されている | ✅ |
| `secret_env_vars` の `dynamic "env"` + `value_source.secret_key_ref` が実装されている | ✅ |
| `google_cloud_run_v2_job_iam_member` で `roles/run.invoker` を付与 | ✅ |
| `outputs.tf` が `job_name` と `job_api_uri` を出力している | ✅ |
| `job_api_uri` が `https://run.googleapis.com/v2/projects/.../jobs/{name}:run` 形式になっている | ✅ |

### terraform/modules/cloud_run（削除）

| チェック項目 | 結果 |
|---|---|
| `terraform/modules/cloud_run/` ディレクトリが削除されている | ✅ |

### terraform/modules/cloud_scheduler（修正）

| チェック項目 | 結果 |
|---|---|
| `variables.tf` に `oidc_audience` 変数が追加されている（デフォルト `""`） | ✅ |
| `main.tf` の OIDC `audience` が `oidc_audience != "" ? oidc_audience : target_url` になっている | ✅ |

### terraform/environments/dev（修正）

| チェック項目 | 結果 |
|---|---|
| `main.tf` の `module "cloud_run"` が `module "cloud_run_job"` に置き換えられている | ✅ |
| `module "cloud_run_job"` の `job_name = "school-agent-v2-dev"` が設定されている | ✅ |
| Cloud Scheduler の `target_url = module.cloud_run_job.job_api_uri` が設定されている | ✅ |
| Cloud Scheduler の `oidc_audience = "https://run.googleapis.com/"` が設定されている | ✅ |
| `outputs.tf` の `service_url` が `job_name` に置き換えられている | ✅ |
| `outputs.tf` の `job_name = module.cloud_run_job.job_name` が設定されている | ✅ |
| `service_account_email` output は維持されている | ✅ |

### Dockerfile（修正）

| チェック項目 | 結果 |
|---|---|
| `CMD` が `["python", "-m", "v2.entrypoints.cli"]` に変更されている | ✅ |
| `functions-framework` 起動コマンドが削除されている | ✅ |
| `RUN cp main_v2.py main.py` が削除されている（CLI 実行では不要） | ✅ |

### deploy_dev.sh（修正）

| チェック項目 | 結果 |
|---|---|
| `terraform output service_url` が `terraform output job_name` に変更されている | ✅ |

---

## テスト・静的解析結果

### terraform validate

```
$ cd terraform/environments/dev && terraform validate
Success! The configuration is valid.
```

**結果**: ✅ PASS（新 cloud_run_job module + 変更された cloud_scheduler module を含む全リソース）

### deploy_dev.sh 構文チェック

```
$ bash -n deploy_dev.sh
syntax OK
```

**結果**: ✅ PASS

### モジュール構成確認

```
$ ls terraform/modules/
artifact_registry
cloud_run_job
cloud_scheduler
secret_manager

$ ls terraform/modules/cloud_run
ls: No such file or directory  ← 削除済み
```

**結果**: ✅ PASS（旧 cloud_run モジュール削除済み、cloud_run_job が存在）

---

## 修正指示

なし（全要件を満たしており、テスト・静的解析もすべて PASS）。
