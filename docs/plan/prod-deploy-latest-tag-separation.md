# prod デプロイ改善計画: latest-prod タグによるワークフロー分離

## 背景・現状

### 現在のデプロイフロー（cd-prod.yml）

```
Git タグ push (v*)
  └─ lint
  └─ test
  └─ deploy
       ├─ Docker build
       ├─ SHA タグ + release タグで push
       ├─ terraform apply -var="image_url=${SHA_URL}"
       └─ apply 成功後のみ prod-latest タグを push
```

**問題点:**
- コンテナビルド/プッシュと Terraform apply が 1 ワークフローに密結合
- インフラ変更のみでもビルドが走る、コンテナ変更のみでも Terraform が走る
- `prod-latest` タグの更新が Terraform apply の成否に依存しており、タイミングが後ろにある
- `tf-cmt-prod.yml` での terraform plan は `prod-latest` を参照するが、CD では SHA タグを渡す（不一致）

---

## 目標

1. Cloud Run Job のイメージ参照を **常に `latest-prod` タグ** に固定する
2. コンテナのビルド/プッシュと Terraform デプロイを **別ワークフローに分離** する
3. ロールバック機能を維持する
4. `tf-cmt-prod.yml`（PR 時の terraform plan）との整合性を保つ

---

## 提案アーキテクチャ

```
【コンテナビルド・プッシュ】             【Terraform デプロイ】
Git タグ push (v*)                    terraform/** の変更 OR workflow_dispatch
        │                                          │
        ▼                                          │
cd-prod-build.yml                                  │
  ├─ lint                                          │
  ├─ test                                          │
  └─ build-push                                    │
       ├─ SHA タグで push                           │
       ├─ release タグで push                       │
       └─ latest-prod タグで push ──────────────────┤
                                    (workflow_run) │
                                                   ▼
                                      cd-prod-terraform.yml
                                        └─ terraform apply
                                             (image_url = ...latest-prod 固定)
                                             Cloud Run Job の image が
                                             latest-prod の現時点 digest に更新される
```

### 分離後のトリガー一覧

| ワークフロー | トリガー | 役割 |
|---|---|---|
| `cd-prod-build.yml` | `push` (tags: `v*`) | 通常デプロイ：ビルド + タグ付け push |
| `cd-prod-build.yml` | `workflow_dispatch` (target_tag) | ロールバック：既存イメージを latest-prod で再タグ付け |
| `cd-prod-terraform.yml` | `workflow_run` (cd-prod-build 完了後) | コンテナ更新に伴う Cloud Run Job 更新 |
| `cd-prod-terraform.yml` | `push` (main, terraform/** 変更) | インフラ変更のみのデプロイ |
| `cd-prod-terraform.yml` | `workflow_dispatch` | 手動デプロイ |
| `tf-cmt-prod.yml` | `pull_request` (terraform/** 変更) | PR 時の terraform plan コメント（変更なし） |

---

## 詳細設計

### 1. タグ命名規則の変更

| 用途 | 現在 | 変更後 |
|---|---|---|
| 最新 prod イメージ | `prod-latest`（Terraform apply 後に付与） | `latest-prod`（ビルド push 時に付与） |
| SHA タグ | `{7桁SHA}` | `{7桁SHA}`（変更なし） |
| release タグ | `{v*}` | `{v*}`（変更なし） |

> **変更の意図**: タグ付与タイミングを「Terraform apply 成功後」から「push 完了時」に前倒しする。
> これにより Terraform との疎結合が実現される。

---

### 2. cd-prod-build.yml（新規ワークフロー）

#### トリガー

```yaml
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      target_tag:
        description: 'ロールバック先の release tag (例: v1.0.0)。指定した場合はそのタグのイメージを latest-prod として再タグ付けします。'
        required: true
```

#### ジョブ構成

```yaml
jobs:
  lint:
    if: github.event_name == 'push'   # ロールバック時はスキップ
    # 既存の lint ジョブと同内容

  test:
    if: github.event_name == 'push'   # ロールバック時はスキップ
    # 既存の test ジョブと同内容

  build-push:
    needs: [lint, test]  # push 時のみ needs が意味を持つ
    # workflow_dispatch 時は needs が空なので即実行される
    environment: prod
    concurrency:
      group: build-prod
      cancel-in-progress: false
    steps:
      # WIF 認証、gcloud 設定（既存と同じ）

      # ── 通常デプロイ（git tag push） ──
      - name: Build and push Docker image (normal deploy)
        if: github.event_name == 'push'
        run: |
          IMAGE_TAG="${GITHUB_SHA::7}"
          RELEASE_TAG="${GITHUB_REF_NAME}"
          BASE="asia-northeast1-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_ID}/${IMAGE_NAME}"

          SHA_URL="${BASE}:${IMAGE_TAG}"
          RELEASE_URL="${BASE}:${RELEASE_TAG}"
          LATEST_PROD_URL="${BASE}:latest-prod"

          # ビルド → 全タグ付与
          docker build --platform linux/amd64 -t "${SHA_URL}" .
          docker tag "${SHA_URL}" "${RELEASE_URL}"
          docker tag "${SHA_URL}" "${LATEST_PROD_URL}"

          # push（latest-prod を含む）
          docker push "${SHA_URL}"
          docker push "${RELEASE_URL}"
          docker push "${LATEST_PROD_URL}"

      # ── ロールバック（workflow_dispatch） ──
      - name: Re-tag for rollback
        if: github.event_name == 'workflow_dispatch'
        run: |
          TARGET_TAG="${{ github.event.inputs.target_tag }}"
          BASE="asia-northeast1-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_ID}/${IMAGE_NAME}"

          TARGET_URL="${BASE}:${TARGET_TAG}"
          LATEST_PROD_URL="${BASE}:latest-prod"

          # 存在確認
          if ! gcloud artifacts docker images describe "${TARGET_URL}" --quiet 2>/dev/null; then
            echo "ERROR: イメージ ${TARGET_URL} が Artifact Registry に存在しません" >&2
            exit 1
          fi

          # 既存イメージを pull → latest-prod として push
          docker pull "${TARGET_URL}"
          docker tag "${TARGET_URL}" "${LATEST_PROD_URL}"
          docker push "${LATEST_PROD_URL}"
```

#### 環境変数

```
LATEST_PROD_URL = asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:latest-prod
SHA_URL         = ...:{7桁SHA}
RELEASE_URL     = ...:{v* タグ}
TARGET_URL      = ...:{target_tag}（ロールバック時）
```

---

### 3. cd-prod-terraform.yml（新規ワークフロー）

#### トリガー

```yaml
on:
  workflow_run:
    workflows: ["Build & Push Prod Image"]   # cd-prod-build.yml の name と一致させる
    types: [completed]

  push:
    branches: [main]
    paths:
      - 'terraform/environments/prod/**'
      - 'terraform/modules/**'

  workflow_dispatch:
```

> **注意**: `workflow_run` はソースワークフローが **成功完了** した場合にのみ Terraform を実行するよう `if: github.event.workflow_run.conclusion == 'success'` でガードする。

#### ジョブ構成

```yaml
jobs:
  deploy:
    if: >
      github.event_name != 'workflow_run' ||
      github.event.workflow_run.conclusion == 'success'
    environment: prod
    concurrency:
      group: deploy-prod
      cancel-in-progress: false
    steps:
      # WIF 認証、gcloud 設定（既存と同じ）

      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "~> 1.5"

      - name: Terraform Init
        working-directory: terraform/environments/prod
        run: terraform init

      - name: Terraform Apply
        working-directory: terraform/environments/prod
        run: |
          terraform apply -auto-approve \
            -var="project_id=${{ env.PROJECT_ID }}" \
            -var="spreadsheet_id=${{ secrets.TF_VAR_SPREADSHEET_ID }}" \
            -var="inbox_folder_id=${{ secrets.TF_VAR_INBOX_FOLDER_ID }}" \
            -var="archive_folder_id=${{ secrets.TF_VAR_ARCHIVE_FOLDER_ID }}"
          # image_url は terraform.tfvars から自動読み込み（CLI 引数不要）
```

---

### 4. Terraform の変更

#### terraform/environments/prod/terraform.tfvars

```hcl
project_id        = "clearbag-prod"
image_url         = "asia-northeast1-docker.pkg.dev/clearbag-prod/school-agent-prod/school-agent-v2:latest-prod"
inbox_folder_id   = "12IMb0DKR7MgGhZCBZGi2EQqHX9T2Dqe7"
spreadsheet_id    = "1uOjIj00ztJlfLzlwKQaZXMYsdCo7Aan41Hz8knkfBTk"
archive_folder_id = "1BsctFITQMnvd_jUsmnad_nYDjj_YWHPo"
```

- `image_url` を `latest-prod` タグの URL に固定（SHA タグ依存を排除）
- CD から `--var image_url=...` を渡す必要がなくなる

#### tf-cmt-prod.yml（変更あり）

PR 時の terraform plan でも `latest-prod` を参照するよう変更（現在は `prod-latest`）:

```yaml
# 変更前
-var="image_url=asia-northeast1-docker.pkg.dev/.../school-agent-v2:prod-latest"

# 変更後
-var="image_url=asia-northeast1-docker.pkg.dev/.../school-agent-v2:latest-prod"
```

> これにより tfcmt による terraform plan と CD の terraform apply が同じ `image_url` を参照するようになり、plan 結果と apply 結果の整合性が保たれる。

---

### 5. 削除するもの

- `.github/workflows/cd-prod.yml`（新 2 ワークフローに置き換え）

---

### 6. 変更しないもの

- `tf-cmt-prod.yml`（image_url の値のみ変更）
- `cd-dev.yml`（dev 環境のデプロイフローは変更なし）
- `terraform/modules/cloud_run_job/main.tf`（モジュール本体は変更なし）
- `terraform/environments/prod/main.tf`（モジュール呼び出し側は変更なし）

---

## ロールバック手順

**新しいロールバック手順:**

1. GitHub Actions UI で `cd-prod-build.yml` を `workflow_dispatch` で実行
2. `target_tag` に戻したいバージョン（例: `v1.0.0`）を入力
3. ワークフローが対象バージョンのイメージを `latest-prod` として再タグ付け・プッシュ
4. `workflow_run` により `cd-prod-terraform.yml` が自動実行
5. Terraform apply が `latest-prod`（= 指定バージョン）で Cloud Run Job を更新

---

## 技術的考慮事項

### Cloud Run Job と mutable タグについて

Cloud Run v2 Job は、イメージ URL を指定する際にタグを **digest（SHA256 ハッシュ）に解決** して保存します。

- Terraform が `image = "...latest-prod"` を指定
- Cloud Run API が `latest-prod` を現時点の digest（例: `sha256:abc123`）に解決して保存
- 次回 `terraform plan` では「指定値: `latest-prod`」vs「実際の状態: `sha256:abc123`」で差分が出る可能性がある

**これは意図した動作です。** `cd-prod-terraform.yml` が実行されるたびに、Cloud Run Job は「その時点での `latest-prod` が指す最新の digest」に更新されます。これが「常に `latest-prod` を見る」という要件を実現します。

### workflow_run トリガーについて

- `workflow_run` はソースワークフローが **どのブランチ/タグで実行されたかに関わらず** トリガーされる
- ただし、downstream ワークフロー（cd-prod-terraform.yml）は **デフォルトブランチ（main）** のコードで実行される
- `cd-prod-build.yml` のコードがデフォルトブランチに存在することが前提（通常は問題なし）

### 初回移行時の注意

1. `latest-prod` タグが Artifact Registry に存在しない状態で Terraform apply が走ると失敗する
2. 移行手順：
   1. 新ワークフローファイルを main にマージ
   2. 最初の Git タグ push を行い `latest-prod` タグを作成
   3. または手動で既存イメージに `latest-prod` タグを付けてから移行

---

## 動作確認項目

### 通常デプロイ

- [ ] Git タグ push で `cd-prod-build.yml` がトリガーされる
- [ ] lint・test が成功する
- [ ] SHA タグ、release タグ、`latest-prod` タグの 3 つが Artifact Registry にプッシュされる
- [ ] `cd-prod-build.yml` 成功完了後、`cd-prod-terraform.yml` が `workflow_run` でトリガーされる
- [ ] Terraform apply が成功し、Cloud Run Job のイメージが `latest-prod` の最新 digest に更新される

### インフラ変更のみ（コンテナ変更なし）

- [ ] `terraform/environments/prod/**` の変更を main に push した場合、`cd-prod-terraform.yml` がトリガーされる
- [ ] コンテナのビルドは実行されない
- [ ] Terraform apply が成功し、インフラ変更が反映される
- [ ] Cloud Run Job のイメージは `latest-prod` の現在の digest に維持される

### ロールバック

- [ ] `workflow_dispatch` で `target_tag` を指定して `cd-prod-build.yml` を実行できる
- [ ] 指定バージョンのイメージが `latest-prod` タグで再プッシュされる
- [ ] `cd-prod-terraform.yml` が自動実行される
- [ ] Cloud Run Job が指定バージョンのイメージで更新される

### tf-cmt（PR 時の terraform plan）

- [ ] `latest-prod` タグを参照した terraform plan が PR コメントに表示される
- [ ] plan 結果が CD の apply と整合している

### 手動 Terraform デプロイ

- [ ] `workflow_dispatch` で `cd-prod-terraform.yml` を手動実行できる

---

## 移行計画

1. Artifact Registry に `latest-prod` タグを手動で作成（既存イメージへの付与）
2. `cd-prod-build.yml` を新規作成
3. `cd-prod-terraform.yml` を新規作成
4. `terraform/environments/prod/terraform.tfvars` の `image_url` を `latest-prod` URL に変更
5. `tf-cmt-prod.yml` の `image_url` を `latest-prod` に変更
6. 上記変更を PR でレビュー・マージ（tfcmt で plan 差分確認）
7. `cd-prod.yml` を削除
8. Git タグ push でテストデプロイを実施し、全確認項目をチェック
