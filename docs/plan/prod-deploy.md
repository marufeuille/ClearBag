# ClearBag 本番環境デプロイ計画

## Context

ClearBag の B2C SaaS 基盤は dev 環境（`clearbag-dev`）で稼働中だが、prod 環境は GCP プロジェクトすら未作成。
既存の `terraform/environments/prod/main.tf` にはインフラの骨格（SA, AR, WIF, Monitoring, Billing）のみ定義されており、
アプリ実体（Cloud Run Service, Firestore, GCS, Cloud Tasks, Secret Manager, Scheduler）がすべて欠落している。
本計画では dev 環境をリファレンスに prod を一から構築する。

---

## Phase 0: 手動セットアップ（GCP/Firebase/シークレット）

> コード変更なし。GCP Console・CLI・Firebase Console で実施。

### 0-1. GCP プロジェクト作成 & Billing 紐付け

```bash
gcloud projects create clearbag-prod --name="ClearBag Prod"
gcloud billing projects link clearbag-prod --billing-account=<BILLING_ACCOUNT_ID>
```

### 0-2. Terraform ブートストラップ用 API 有効化

Terraform が管理する API の有効化は `google_project_service` で行うが、Terraform 自体の実行に必要な最低限の API は手動で有効化:

```bash
gcloud services enable \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  sts.googleapis.com \
  iamcredentials.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  --project=clearbag-prod
```

### 0-3. Terraform state バケット作成

```bash
gcloud storage buckets create gs://clearbag-prod-terraform-backend \
  --project=clearbag-prod \
  --location=asia-northeast1 \
  --uniform-bucket-level-access
```

### 0-4. Firebase プロジェクト設定

```bash
firebase projects:addfirebase clearbag-prod
```

Firebase Console で:
1. **Authentication** > Google sign-in 有効化
2. **Firestore** > `asia-northeast1` に Native mode で DB 作成
3. **Hosting** > 初期化（デプロイは CI から実施）
4. **Web アプリ追加** > 設定値（API_KEY, AUTH_DOMAIN, APP_ID 等）を控える

### 0-5. VAPID キー生成

```bash
npx web-push generate-vapid-keys
```

Public key → GitHub Secrets (`NEXT_PUBLIC_VAPID_PUBLIC_KEY`) + Terraform 環境変数
Private key → Phase 1 の Terraform apply 後に Secret Manager へ格納:

```bash
echo -n "<PRIVATE_KEY>" | gcloud secrets versions add clearbag-vapid-private-key-prod \
  --project=clearbag-prod --data-file=-
```

### 0-6. ローカルから初回 Terraform apply（WIF ブートストラップ）

Phase 1 のコード変更後、ローカル ADC でまず WIF + SA + AR だけを作成。
Cloud Run Service のイメージがまだ存在しないため、2段階 apply が必要:

**ステップ A**: `api_service`, `morning_digest_scheduler`, `event_reminder_scheduler` モジュールを一時コメントアウトして apply
**ステップ B**: プレースホルダイメージを push

```bash
docker pull gcr.io/cloudrun/hello
docker tag gcr.io/cloudrun/hello asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:latest-prod
gcloud auth configure-docker asia-northeast1-docker.pkg.dev --quiet
docker push asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:latest-prod
```

**ステップ C**: コメントアウトを戻して再度 apply → Cloud Run Service + Scheduler が作成される

### 0-7. billing.costsManager 手動付与

```bash
gcloud billing accounts add-iam-policy-binding <BILLING_ACCOUNT_ID> \
  --member="serviceAccount:github-actions-deploy-prod@clearbag-prod.iam.gserviceaccount.com" \
  --role="roles/billing.costsManager"
```

### 0-8. 確認チェックリスト

- [ ] `gcloud projects describe clearbag-prod` が正常
- [ ] `gsutil ls gs://clearbag-prod-terraform-backend` が正常
- [ ] `firebase projects:list` に `clearbag-prod` 表示
- [ ] Firebase Auth Google sign-in 有効
- [ ] VAPID キーペア生成済み

---

## Phase 1: Terraform prod/main.tf 書き換え

### 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `terraform/environments/prod/main.tf` | B2C 基盤リソース追加（~130行追加） |
| `terraform/environments/prod/variables.tf` | 変数 3 つ追加 |
| `terraform/environments/prod/terraform.tfvars` | バッチ時代の値を削除 |
| `terraform/environments/prod/outputs.tf` | `api_service_url` 追加 |

### 1-1. `main.tf` に追加する GCP API リソース

`billingbudgets`/`cloudbilling` は既存。以下 7 つを追加:

```
google_project_service.sts                  (sts.googleapis.com)
google_project_service.iamcredentials       (iamcredentials.googleapis.com)
google_project_service.cloudresourcemanager  (cloudresourcemanager.googleapis.com)
google_project_service.firestore            (firestore.googleapis.com)
google_project_service.cloudtasks           (cloudtasks.googleapis.com)
google_project_service.firebase             (firebase.googleapis.com)
google_project_service.firebasehosting      (firebasehosting.googleapis.com)
```

参考: dev/main.tf:87-171

### 1-2. WIF module に `depends_on` 追加

現状 prod の `module "workload_identity"` に `depends_on` がない（dev:111-114 にはある）。
`google_project_service.sts` と `google_project_service.iamcredentials` への依存を追加。

### 1-3. GitHub Actions IAM ロール 3 つ追加

`github_actions_prod_roles` local に追加:
- `roles/datastore.owner` — Firestore 管理
- `roles/cloudtasks.admin` — Cloud Tasks キュー管理
- `roles/firebasehosting.admin` — Firebase Hosting デプロイ

参考: dev/main.tf:130-132

### 1-4. Cloud Run SA self-actAs IAM 追加

Cloud Tasks の OIDC トークン生成に必要。prod に欠落中。

```hcl
resource "google_service_account_iam_member" "cloud_run_self_actas" {
  service_account_id = google_service_account.cloud_run.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cloud_run.email}"
}
```

参考: dev/main.tf:50-56

### 1-5. B2C モジュール追加（7 モジュール）

| モジュール | prod 固有設定 | 参考 |
|---|---|---|
| `module "firestore"` | `deletion_policy = "ABANDON"` (prod安全策) | dev:179-192 |
| `module "cloud_storage_uploads"` | bucket: `clearbag-prod-clearbag-uploads-prod`, lifecycle: 365日 | dev:194-201 |
| `module "cloud_tasks_analysis"` | queue: `clearbag-analysis-prod` | dev:203-219 |
| `module "secret_vapid_private_key"` | secret: `clearbag-vapid-private-key-prod` | dev:221-227 |
| `module "api_service"` | 下記参照 | dev:229-274 |
| `module "morning_digest_scheduler"` | job: `clearbag-morning-digest-prod` | dev:314-327 |
| `module "event_reminder_scheduler"` | job: `clearbag-event-reminder-prod` | dev:329-343 |

**Firestore の `import` ブロック**: Firebase Console で Firestore を先に作成した場合は必要:

```hcl
import {
  to = module.firestore.google_firestore_database.this
  id = "projects/clearbag-prod/databases/(default)"
}
```

### 1-6. `api_service` の prod 固有設定

dev との主要差分:

| 環境変数 | dev | prod |
|---|---|---|
| `DISABLE_RATE_LIMIT` | `"true"` | **設定しない**（rate limit 有効） |
| `CORS_ORIGINS` | `clearbag-dev.web.app,...` | `clearbag-prod.web.app,clearbag-prod.firebaseapp.com` |
| `FRONTEND_BASE_URL` | `clearbag-dev.web.app` | `clearbag-prod.web.app` |
| `API_BASE_URL` | `clearbag-api-dev-...` | `clearbag-api-prod-...` |
| `WORKER_URL` | `clearbag-api-dev-.../worker/analyze` | `clearbag-api-prod-.../worker/analyze` |
| service_name | `clearbag-api-dev` | `clearbag-api-prod` |

### 1-7. `variables.tf` — 変数 3 つ追加

```hcl
variable "api_image_url" {
  description = "B2C API サーバーのコンテナイメージ URL（deploy 時に -var で渡す）"
  type        = string
  default     = "asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:latest-prod"
}

variable "allowed_emails" {
  description = "ログイン許可メールアドレス（カンマ区切り）。未設定の場合は全員許可。"
  type        = string
  default     = ""
}

variable "vapid_claims_email" {
  description = "Web Push VAPID クレームの連絡先メールアドレス（mailto: に使用）"
  type        = string
  default     = ""
}
```

### 1-8. `terraform.tfvars` — クリーンアップ

バッチ時代の `image_url`, `inbox_folder_id`, `spreadsheet_id`, `archive_folder_id` を削除。
`project_id = "clearbag-prod"` のみ残す。

### 1-9. `outputs.tf` — 追加

```hcl
output "api_service_url" {
  description = "B2C API Cloud Run Service の URL（フロントエンド NEXT_PUBLIC_API_BASE_URL に設定）"
  value       = module.api_service.service_url
}
```

---

## Phase 2: CI/CD ワークフロー更新

### 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `.github/workflows/cd-prod-terraform.yml` | Terraform vars 追加 + フロントエンドデプロイジョブ追加 |
| `.github/workflows/tf-cmt-prod.yml` | PR トリガー有効化 + vars 追加 |

### 2-1. `cd-prod-terraform.yml` — Terraform Apply 修正

現状（行 60-63）: `IMAGE_URL` を解決するが Terraform に渡していない。

修正後:
```yaml
terraform apply -auto-approve \
  -var="api_image_url=${IMAGE_URL}" \
  -var="project_id=${{ env.PROJECT_ID }}" \
  -var="notification_email=${{ secrets.TF_VAR_NOTIFICATION_EMAIL }}" \
  -var="allowed_emails=${{ secrets.TF_VAR_ALLOWED_EMAILS }}" \
  -var="billing_account_id=${{ secrets.TF_VAR_BILLING_ACCOUNT_ID }}" \
  -var="vapid_claims_email=${{ secrets.TF_VAR_VAPID_CLAIMS_EMAIL }}"
```

+ Terraform output 取得ステップ追加（`api_service_url`）
+ `deploy` ジョブに `outputs:` 追加

### 2-2. `cd-prod-terraform.yml` — `deploy-frontend` ジョブ追加

`cd-dev.yml:170-234` をベースに prod 用に作成:
- `needs: [deploy]` で Terraform deploy 完了後に実行
- Cloud Run URL を `deploy.outputs.api_service_url` から取得（フォールバック: `gcloud run services describe`）
- `NEXT_PUBLIC_*` 環境変数を `secrets.*` から注入
- `npm ci` → `npm run build` → `firebase deploy --only hosting --project clearbag-prod`

### 2-3. `cd-prod-terraform.yml` — `notify` ジョブ更新

`needs` に `deploy-frontend` を追加、`result` 判定に含める。

### 2-4. `tf-cmt-prod.yml` — PR トリガー有効化

行 4-8 のコメントアウトを解除:

```yaml
on:
  pull_request:
    paths:
      - "terraform/environments/prod/**"
      - "terraform/modules/**"
  workflow_dispatch:
```

+ plan コマンドに `-var="allowed_emails=..."` と `-var="vapid_claims_email=..."` 追加

---

## Phase 3: GitHub Secrets 設定

GitHub Environment `prod` に以下を追加:

### 既存 Secrets（Phase 0 で設定済みのはず）

| Secret | 値の取得元 |
|---|---|
| `WIF_PROVIDER` | `terraform output workload_identity_provider` |
| `WIF_SERVICE_ACCOUNT` | `terraform output github_actions_service_account_email` |
| `TF_VAR_NOTIFICATION_EMAIL` | 通知先メールアドレス |
| `TF_VAR_BILLING_ACCOUNT_ID` | GCP 請求先アカウント ID |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

### 新規追加 Secrets（9 個）

| Secret | 値 |
|---|---|
| `TF_VAR_ALLOWED_EMAILS` | カンマ区切りの許可メールアドレス |
| `TF_VAR_VAPID_CLAIMS_EMAIL` | VAPID 連絡先メールアドレス |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase Console > Web アプリ設定 |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | `clearbag-prod.firebaseapp.com` |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | `clearbag-prod` |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | `clearbag-prod.firebasestorage.app` |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase Console |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase Console |
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | Phase 0-5 で生成した公開鍵 |

```bash
# 一括設定例
gh secret set TF_VAR_ALLOWED_EMAILS --env prod --body "..."
gh secret set NEXT_PUBLIC_FIREBASE_API_KEY --env prod --body "..."
# ... (全 9 個)
```

---

## Phase 4: 初回デプロイ & 検証

### 4-1. デプロイ手順

1. **PR 作成**: Phase 1-2 のコード変更をブランチに push → PR
   - `tf-cmt-prod.yml` が Terraform plan をコメント（~20 リソース追加を確認）
2. **PR マージ** → `cd-dev.yml` 実行（dev のみ、prod 影響なし）
3. **タグ push**: `git tag v1.0.0 && git push origin v1.0.0`
   - `cd-prod-build.yml`: lint → test → Docker build → push（3 タグ）
   - `cd-prod-terraform.yml`: terraform apply → firestore rules → frontend deploy
4. **CI 監視**:
   ```bash
   gh run list
   gh run watch <run-id>
   ```

### 4-2. 検証チェックリスト

```bash
# バックエンド API
curl https://clearbag-api-prod-<NUMBER>.asia-northeast1.run.app/health

# フロントエンド
curl -I https://clearbag-prod.web.app

# Firestore
gcloud firestore databases describe --project=clearbag-prod

# Cloud Tasks
gcloud tasks queues describe clearbag-analysis-prod \
  --location=asia-northeast1 --project=clearbag-prod

# Cloud Scheduler
gcloud scheduler jobs list --location=asia-northeast1 --project=clearbag-prod
```

### 4-3. E2E 動作確認

1. `https://clearbag-prod.web.app` にアクセス
2. Google ログイン（`ALLOWED_EMAILS` に含まれるアカウント）
3. テスト PDF アップロード → 解析完了を確認
4. カレンダーイベント・タスク表示を確認
5. Push 通知の受信を確認

---

## Phase 5: デプロイ後タスク

### 5-1. 初期ユーザーアクティベーション

```bash
PROJECT_ID=clearbag-prod uv run python scripts/activate_existing_users.py --email <EMAIL>
```

### 5-2. Scheduler 手動実行テスト

```bash
gcloud scheduler jobs run clearbag-morning-digest-prod --location=asia-northeast1 --project=clearbag-prod
gcloud scheduler jobs run clearbag-event-reminder-prod --location=asia-northeast1 --project=clearbag-prod
```

### 5-3. prod URL の記録

| 用途 | URL |
|---|---|
| フロントエンド | `https://clearbag-prod.web.app` |
| API | `https://clearbag-api-prod-<NUMBER>.asia-northeast1.run.app` |
| Swagger UI | `https://clearbag-api-prod-<NUMBER>.asia-northeast1.run.app/docs` |

---

## リスクと対策

| リスク | 対策 |
|---|---|
| 初回 apply 時にイメージ未存在 | Phase 0-6 でプレースホルダイメージを push |
| Firestore が Console で先に作成される | `import` ブロックを追加（Phase 1-5 参照） |
| Secret Manager にバージョン未格納 | Phase 0-5 で VAPID private key を格納してから apply |
| ALLOWED_EMAILS 空 → 全員アクセス可 | 初期は制限付きで運用し、安定後に開放を検討 |
