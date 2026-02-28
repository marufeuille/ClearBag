# prod 環境デプロイ計画

## 目標

GitHub の tag push (`v*`) をトリガーとして、GitHub Actions 経由で prod 環境へ自動デプロイする仕組みを構築する。
既存の手動デプロイ済み prod 環境は、新環境が正常稼働後に削除する。

---

## 現状確認

| 項目 | dev 環境 (現状) | prod 環境 (今回構築) |
|------|----------------|---------------------|
| トリガー | `main` ブランチ push | GitHub tag push (`v*`) |
| イメージタグ (Terraform) | `:latest` | `:<sha7>` (+ `prod-latest` エイリアス) |
| Artifact Registry | `school-agent-dev` | `school-agent-prod` (新規) |
| WIF | `github-actions` pool + `github-actions-deploy` SA | 同 pool を参照、`github-actions-deploy-prod` SA を新規作成 |
| GCP プロジェクト | `clearbag-prod` | 同一プロジェクト (現状に合わせる) |

---

## イメージタグ戦略の決定

### dev vs prod の問題

dev は `latest` タグを使うため、`main` push のたびに `latest` が更新される。
GCP Cloud Run Jobs は **Job 更新時点のイメージダイジェストを内部的に固定する**仕様のため、
`prod-latest` のような可変タグを Terraform の `image_url` にしても、タグが更新されるだけでは
Job 定義が変わらず、Terraform apply が no-op になり新イメージが反映されない。

### 採用方針

- Terraform `image_url` には **`<sha7>` タグ** を使用する
  → 毎回異なる URL になるため Terraform が差分を検出し Cloud Run Job を更新する
- **`prod-latest` タグも同時に push** する
  → オペレーター参照・ロールバック確認用の安定したエイリアスとして機能する
  → このタグは GitHub tag push 時のみ更新されるため、dev の `latest` とは明確に区別できる

```
asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:<sha7>   ← Terraform が参照
asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:prod-latest  ← エイリアス
asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:v1.2.3  ← GitHub tag 名と同一
```

---

## Terraform 構成

### ディレクトリ構造

```
terraform/
├── environments/
│   ├── dev/          # 既存 (変更なし)
│   └── prod/         # 新規作成
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── terraform.tfvars
└── modules/          # 既存モジュールを流用 (変更なし)
```

### backend 設定

```hcl
backend "gcs" {
  bucket = "clearbag-prod-terraform-backend"
  prefix = "terraform/environments/prod"
}
```

既存の dev と同一バケットの別 prefix を使用する。

### 作成リソース一覧

| リソース種別 | リソース名 | 備考 |
|-------------|-----------|------|
| Service Account | `school-agent-v2-prod` | Cloud Run Job 実行用 |
| IAM binding | `roles/aiplatform.user` → 上記 SA | Vertex AI 呼び出し権限 |
| IAM binding | `roles/iam.serviceAccountTokenCreator` → Cloud Scheduler SA | スケジューラー呼び出し権限 |
| Artifact Registry | `school-agent-prod` | prod 専用リポジトリ |
| Secret Manager | `school-agent-slack-bot-token-prod` | |
| Secret Manager | `school-agent-slack-channel-id-prod` | |
| Secret Manager | `school-agent-todoist-api-token-prod` | |
| Cloud Run Job | `school-agent-v2-prod` | |
| Cloud Scheduler | `school-agent-v2-scheduler-prod` | スケジュールは dev と同じ `0 9,17 * * *` を初期値に |
| Service Account | `github-actions-deploy-prod` | GitHub Actions デプロイ用 |
| WIF binding | 既存 pool への SA バインド | pool/provider は dev Terraform 管理のものを ID 指定で参照 |
| IAM bindings | 各種権限 → `github-actions-deploy-prod` SA | 下記参照 |

### GitHub Actions SA に付与する IAM ロール (prod)

dev と同一セットを prod スコープで付与:

```
roles/artifactregistry.writer          # Docker push
roles/run.developer                    # Cloud Run Job 更新
roles/iam.serviceAccountUser           # Cloud Run SA として実行
roles/storage.admin                    # Terraform state (GCS)
roles/cloudscheduler.admin             # Cloud Scheduler 管理
roles/resourcemanager.projectIamAdmin  # IAM ポリシー変更
roles/secretmanager.admin              # Secret Manager 管理
roles/serviceusage.serviceUsageAdmin   # API 有効化
roles/iam.serviceAccountAdmin          # SA 作成・管理
```

### WIF の取り扱い

WIF Pool・Provider は dev Terraform で管理済みのため、prod Terraform では新規作成しない。
prod SA (`github-actions-deploy-prod`) を既存 pool に WIF バインドする:

```hcl
resource "google_service_account_iam_member" "wif_binding_prod" {
  service_account_id = google_service_account.github_actions_prod.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions/attribute.repository/marufeuille/ClearBag"
}
```

`<PROJECT_NUMBER>` は `data "google_project"` で動的取得する。

---

## GitHub Actions ワークフロー

### ファイル: `.github/workflows/cd-prod.yml`

```
on:
  push:
    tags:
      - 'v*'
```

#### ジョブ構成

1. **lint** - dev と同じ ruff lint チェック
2. **test** - dev と同じ pytest 実行
3. **deploy** (needs: [lint, test])
   - Environment: `prod`
   - concurrency: `deploy-prod`
   - 手順:
     1. WIF 認証 (prod secrets: `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`)
     2. Docker 認証
     3. `uv export` で requirements.txt 生成
     4. イメージビルド
        - `IMAGE_TAG = "${GITHUB_SHA::7}"`  (SHA タグ)
        - `RELEASE_TAG = "${GITHUB_REF_NAME}"` (例: `v1.2.3`)
        - SHA URL: `<registry>/school-agent-prod/school-agent-v2:<sha7>`
        - `prod-latest` URL: `<registry>/school-agent-prod/school-agent-v2:prod-latest`
        - Release tag URL: `<registry>/school-agent-prod/school-agent-v2:<v1.2.3>`
     5. 3タグすべて push
     6. Terraform init / apply
        - `working-directory: terraform/environments/prod`
        - `-var="image_url=${SHA_URL}"` ← SHA タグで固定

#### Terraform apply に渡す変数

| 変数名 | 設定方法 |
|--------|---------|
| `project_id` | ワークフロー env または secrets |
| `image_url` | ビルド時の SHA URL を `$GITHUB_ENV` 経由で渡す |
| `spreadsheet_id` | GitHub Environment Secret: `TF_VAR_SPREADSHEET_ID` |
| `inbox_folder_id` | GitHub Environment Secret: `TF_VAR_INBOX_FOLDER_ID` |
| `archive_folder_id` | GitHub Environment Secret: `TF_VAR_ARCHIVE_FOLDER_ID` |

---

## GitHub 設定 (手動作業)

### Environment `prod` の作成

GitHub リポジトリ Settings → Environments → New environment で `prod` を作成し、
以下の Secrets を設定する:

| Secret 名 | 内容 |
|-----------|------|
| `WIF_PROVIDER` | Terraform apply 後に出力される prod SA の WIF Provider パス |
| `WIF_SERVICE_ACCOUNT` | `github-actions-deploy-prod` SA のメールアドレス |
| `TF_VAR_SPREADSHEET_ID` | prod 用 Google スプレッドシート ID |
| `TF_VAR_INBOX_FOLDER_ID` | prod 用 受信フォルダ ID |
| `TF_VAR_ARCHIVE_FOLDER_ID` | prod 用 アーカイブフォルダ ID |

> オプション: Environment の Protection rules で「Required reviewers」を設定すると、
> tag push 後に手動承認が必要になり誤デプロイを防止できる。

### Secret Manager への値の手動投入

Terraform は Secret のリソース（シェル）を作成するが、値は別途投入が必要:

```bash
echo -n "<SLACK_BOT_TOKEN>" | gcloud secrets versions add school-agent-slack-bot-token-prod --data-file=-
echo -n "<SLACK_CHANNEL_ID>" | gcloud secrets versions add school-agent-slack-channel-id-prod --data-file=-
echo -n "<TODOIST_API_TOKEN>" | gcloud secrets versions add school-agent-todoist-api-token-prod --data-file=-
```

---

## デプロイ手順

### Phase 1: Terraform prod 環境の初期構築

```
前提: terraform/environments/prod/ ファイルを作成済み
```

1. 初回は GitHub Actions を使わず、ローカルから初期化のみ実施
   ```bash
   cd terraform/environments/prod
   terraform init
   # (plan で確認後)
   terraform apply -var="image_url=dummy" -var="project_id=..." ...
   ```
   ※ `image_url=dummy` で一旦インフラだけ構築。Cloud Run Job は後で正しいイメージで上書き。

   **または**: 初回デプロイは tag を push して Actions 経由で実施 (推奨)
   → Artifact Registry や Secret Manager 等がないと Actions が失敗するため、
     先に Terraform で `exclude_resources = [cloud_run_job, cloud_scheduler]` 的に部分 apply するか、
     Actions の deploy ジョブを 2 段階に分けることを検討する

2. Terraform outputs から WIF 情報を取得し、GitHub Environment Secrets に設定
3. Secret Manager に値を投入

### Phase 2: 初回 prod リリース

1. Secret Manager に prod の各シークレット値を投入 (上記コマンド)
2. main ブランチで動作確認完了後、tag を打つ:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. GitHub Actions `cd-prod.yml` が起動 → テスト → イメージビルド → Terraform apply
4. Cloud Run Job が正常に実行されることを確認

### Phase 3: 既存手動デプロイの削除

新環境が正常稼働していることを確認後、手動デプロイで作成したリソースを削除:

```bash
# 手動でデプロイされた Cloud Run Job (名前を確認の上)
gcloud run jobs delete <OLD_PROD_JOB_NAME> --region=asia-northeast1

# 手動でデプロイされた Cloud Scheduler (あれば)
gcloud scheduler jobs delete <OLD_PROD_SCHEDULER_NAME> --location=asia-northeast1

# 手動で作成した Service Account (あれば、かつ Terraform 管理外であれば)
# gcloud iam service-accounts delete <OLD_SA_EMAIL>
```

> Terraform 管理対象のリソースは `terraform destroy` を使わないこと。

---

## ロールバック戦略

### 前提: ロールバックが可能な理由

Terraform `image_url` に SHA タグを使っているため、以下が担保される:

- Artifact Registry に各バージョンのイメージが残る (`v1.0.0`, `v1.1.0` など)
- Terraform state に「どの SHA で何の Job が動いているか」が記録される
- 過去の SHA URL を Terraform apply に渡せば、任意のバージョンに戻せる

**Artifact Registry のクリーンアップポリシーに注意**: ロールバック用イメージが自動削除されないよう、
prod リポジトリではクリーンアップポリシーを設定しないか、最低でも過去 N バージョンを保持する設定にする。

---

### ロールバック手順

#### 方法1: GitHub Actions の workflow_dispatch でロールバック（推奨）

`cd-prod.yml` に `workflow_dispatch` トリガーと `target_tag` 入力を追加する:

```yaml
on:
  push:
    tags: ['v*']
  workflow_dispatch:
    inputs:
      target_tag:
        description: 'ロールバック先の release tag (例: v1.0.0)'
        required: true
```

ロールバック時の操作:
```
GitHub Actions → Run workflow → target_tag に "v1.0.0" を入力 → 実行
```

ワークフロー内では:
- `target_tag` 入力がある場合: `git checkout <target_tag>` してそのコードをビルド
- ただし、**イメージはすでに Artifact Registry に存在**するため、再ビルドしない
  → Artifact Registry に `v1.0.0` タグのイメージが存在すれば、それを Terraform に渡すだけで良い

```yaml
- name: Resolve rollback image
  if: github.event_name == 'workflow_dispatch'
  run: |
    TARGET_TAG="${{ github.event.inputs.target_tag }}"
    SHA_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_ID}/${IMAGE_NAME}:${TARGET_TAG}"
    echo "SHA_URL=${SHA_URL}" >> $GITHUB_ENV
    # prod-latest は更新しない（ロールバック中は現在の prod-latest を維持）
```

**メリット**: Terraform state と実際のリソースが一致したまま

---

#### 方法2: 緊急ロールバック（手動 gcloud）

デプロイパイプラインが壊れていて Actions が使えない緊急時:

```bash
# ロールバック先のイメージ URL を確認 (例: v1.0.0 タグ)
ROLLBACK_URL="asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:v1.0.0"

# Cloud Run Job を直接更新
gcloud run jobs update school-agent-v2-prod \
  --image="${ROLLBACK_URL}" \
  --region=asia-northeast1
```

**注意**: この操作は Terraform state と実際のリソースを乖離させる。
次回 `terraform apply` 時に最新の Terraform 設定（最後に apply した SHA）に上書きされるため、
緊急ロールバック後は必ず方法1でロールバックを Terraform 管理下に戻すこと。

---

#### 方法3: 旧バージョンタグで新 release tag を切る（コードレベルでのロールバック）

v1.1.0 で問題が発生し、v1.0.0 のコードに戻したい場合:

```bash
git checkout v1.0.0
git checkout -b hotfix/rollback-to-v1.0.0
# 必要であれば最小限の修正を加えて
git tag v1.1.1
git push origin v1.1.1
```

`cd-prod.yml` が起動し、v1.0.0 相当のコードで `v1.1.1` イメージをビルドしてデプロイ。
コードとリリース履歴が明示的に残る。

---

### ロールバック判断基準

Cloud Run Jobs は定時実行 (Scheduler) のため、デプロイ直後に次の定時実行が来るまで問題に気づかない可能性がある。

| 問題の種類 | 確認方法 | 対応 |
|-----------|---------|------|
| Job がクラッシュする | Cloud Logging でエラー確認 | 方法1 または 方法2 |
| Job は成功するが出力が不正 | Slack 通知・スプレッドシートの確認 | 方法1 |
| Actions パイプラインが壊れている | GitHub Actions のログ確認 | 方法2 |
| コードレベルの問題 | テスト・ログ解析 | 方法3 |

---

### prod-latest タグのロールバック時の扱い

- **通常デプロイ時**: `prod-latest` を最新 SHA に更新する
- **ロールバック時 (方法1・2)**: `prod-latest` は**更新しない**
  → ロールバック中であることを明示するため、`prod-latest` が最新リリースを指さない状態を許容する
  → または `prod-latest` もロールバック先の SHA に戻すことで「現在動いているイメージ = prod-latest」を維持する

設計判断: `prod-latest` は「現在 prod で動いているイメージ」を常に指すようにするのが望ましい。
ワークフローでは Terraform apply 成功後に `prod-latest` を更新するステップを配置する。

---

## 考慮事項・制約

### GCP プロジェクト分離

dev (`clearbag-dev`) と prod (`clearbag-prod`) は別プロジェクト:
- WIF Pool/Provider はそれぞれのプロジェクト内に独立して作成
- dev と prod の Terraform state も別バケット (`clearbag-dev-terraform-backend` / `clearbag-prod-terraform-backend`) で管理
- プロジェクト分離により本番環境への意図しない変更リスクを排除

### 初回 Terraform apply の課題

Cloud Run Job の image_url に有効なイメージが必要なため、以下のいずれかで対応:
1. **Actions 経由**: Terraform plan のみ先行し、イメージ push 後に apply (推奨)
2. **ローカル先行**: インフラ部分 (AR, SA, Secrets) を先に apply → tag push で Cloud Run Job 含めて apply

### Cloud Run Job のイメージ更新確認

tag push → Actions → terraform apply が成功したら:
```bash
gcloud run jobs describe school-agent-v2-prod --region=asia-northeast1 --format="get(template.template.containers[0].image)"
```
で SHA タグが反映されているか確認する。

---

## ファイル変更サマリー

| ファイル | 操作 |
|---------|------|
| `terraform/environments/prod/main.tf` | 新規作成 |
| `terraform/environments/prod/variables.tf` | 新規作成 |
| `terraform/environments/prod/outputs.tf` | 新規作成 |
| `terraform/environments/prod/terraform.tfvars` | 新規作成 (非シークレット値のみ) |
| `.github/workflows/cd-prod.yml` | 新規作成 |
| `terraform/environments/dev/` | 変更なし |
| `terraform/modules/` | 変更なし |
