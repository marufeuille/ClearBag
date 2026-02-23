# レビューレポート: prod-deploy

## 全体ステータス

**PASS**

---

## 要件カバレッジ

### Terraform ファイル

| 要件 | 状態 | 備考 |
|------|------|------|
| `terraform/environments/prod/main.tf` 新規作成 | ✅ | |
| `terraform/environments/prod/variables.tf` 新規作成 | ✅ | |
| `terraform/environments/prod/outputs.tf` 新規作成 | ✅ | |
| `terraform/environments/prod/terraform.tfvars` 新規作成 | ✅ | |
| GCS backend (`prefix = "terraform/environments/prod"`) | ✅ | |
| `terraform/environments/dev/` 変更なし | ✅ | |

### 作成リソース

| 要件リソース | リソース名 | 状態 |
|-------------|-----------|------|
| Cloud Run 実行 SA | `school-agent-v2-prod` | ✅ |
| IAM: `roles/aiplatform.user` → 実行 SA | — | ✅ |
| IAM: `roles/iam.serviceAccountTokenCreator` → Scheduler SA | — | ✅ |
| Artifact Registry (prod 専用) | `school-agent-prod` | ✅ |
| Secret Manager: slack-bot-token | `school-agent-slack-bot-token-prod` | ✅ |
| Secret Manager: slack-channel-id | `school-agent-slack-channel-id-prod` | ✅ |
| Secret Manager: todoist-api-token | `school-agent-todoist-api-token-prod` | ✅ |
| Cloud Run Job | `school-agent-v2-prod` | ✅ |
| Cloud Scheduler (`0 9,17 * * *`) | `school-agent-v2-scheduler-prod` | ✅ |
| GitHub Actions デプロイ用 SA | `github-actions-deploy-prod` | ✅ |
| WIF Pool/Provider/SA バインド | — | ✅ (後述の改善点参照) |

### GitHub Actions SA IAM ロール

| ロール | 状態 |
|--------|------|
| `roles/artifactregistry.writer` | ✅ |
| `roles/run.developer` | ✅ |
| `roles/iam.serviceAccountUser` | ✅ |
| `roles/storage.admin` | ✅ |
| `roles/cloudscheduler.admin` | ✅ |
| `roles/resourcemanager.projectIamAdmin` | ✅ |
| `roles/secretmanager.admin` | ✅ |
| `roles/serviceusage.serviceUsageAdmin` | ✅ |
| `roles/iam.serviceAccountAdmin` | ✅ |
| `roles/iam.workloadIdentityPoolAdmin` | ✅ (prod WIF Pool 管理のため追加、正当) |

### GitHub Actions ワークフロー (`.github/workflows/cd-prod.yml`)

| 要件 | 状態 |
|------|------|
| トリガー: `push: tags: ['v*']` | ✅ |
| トリガー: `workflow_dispatch` + `target_tag` 入力 (ロールバック用) | ✅ |
| `lint` ジョブ (ruff check / format) | ✅ |
| `test` ジョブ (pytest, `not manual`) | ✅ |
| `deploy` ジョブ (`needs: [lint, test]`) | ✅ |
| `environment: prod` 指定 | ✅ |
| `concurrency: deploy-prod` (cancel-in-progress: false) | ✅ |
| WIF 認証 (`WIF_PROVIDER` / `WIF_SERVICE_ACCOUNT`) | ✅ |
| Docker 認証 (Artifact Registry) | ✅ |
| `uv export` → Docker build (push イベント時のみ) | ✅ |
| SHA タグ + release タグ push | ✅ |
| Terraform には SHA URL を渡す | ✅ |
| ロールバック時: 既存イメージの存在確認 + 再ビルドなし | ✅ |
| Terraform apply (通常・ロールバック共通) | ✅ |
| `prod-latest` 更新は Terraform apply 成功後のみ (push 時) | ✅ |

### イメージタグ戦略

| 要件 | 状態 |
|------|------|
| Terraform `image_url` に SHA タグ使用 (毎回差分を検出) | ✅ |
| `prod-latest` タグを push イベント時に Artifact Registry へ push | ✅ |
| release タグ (`v1.x.x`) を同時 push | ✅ |
| `prod-latest` は apply 成功後にのみ更新 | ✅ |

---

## プランからの変更点（合意済み）

プランの「modules/ 変更なし」の記述に反し、以下の変更が加えられた。これはユーザーとの対話で合意された必要な変更であり、正当と判断する。

| 変更ファイル | 変更内容 | 評価 |
|------------|---------|------|
| `modules/workload_identity/variables.tf` | `pool_id`・`sa_account_id` 変数を追加（デフォルト値あり） | ✅ 後方互換性維持 |
| `modules/workload_identity/main.tf` | pool_id・account_id をハードコードから変数参照に変更 | ✅ dev への影響なし |
| `prod/main.tf` の WIF 設計 | dev WIF Pool 参照ではなく prod 専用 Pool を作成 | ✅ 要求に沿った改善 |

---

## テスト・静的解析結果

### Terraform validate

```
# prod 環境
$ terraform init -backend=false && terraform validate
Success! The configuration is valid.

# dev 環境（後方互換確認）
$ terraform init -backend=false && terraform validate
Success! The configuration is valid.
```

### ruff lint / format

```
$ uv run ruff check v2/
All checks passed!

$ uv run ruff format --check v2/
21 files already formatted
```

### pytest

```
$ uv run pytest tests/unit/ tests/integration/ -m "not manual" -q
37 passed, 3 deselected in 0.30s
```

---

## 修正指示

なし（全テスト・静的解析 PASS、全要件カバー済み）
