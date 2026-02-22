# レビューレポート: container-deploy-artifact-registry

**日付**: 2026-02-22
**レビュアー**: /reviewer skill
**仕様書**: `docs/plan/container-deploy-artifact-registry.md`

---

## 全体ステータス

**✅ PASS**

---

## 要件カバレッジ

### Step 1: Terraform module — Artifact Registry

| チェック項目 | 結果 |
|---|---|
| `terraform/modules/artifact_registry/variables.tf` が新規作成されている | ✅ |
| 変数 `project_id`, `region`, `repository_id`, `environment` が定義されている | ✅ |
| `terraform/modules/artifact_registry/main.tf` が新規作成されている | ✅ |
| `google_artifact_registry_repository` リソースが `format = "DOCKER"` で定義されている | ✅ |
| `labels` に `environment` と `managed_by = "terraform"` が設定されている | ✅ |
| `terraform/modules/artifact_registry/outputs.tf` が新規作成されている | ✅ |
| `registry_url` 出力が `{region}-docker.pkg.dev/{project_id}/{repository_id}` 形式 | ✅ |
| `image_base` 出力が `{registry_url}/school-agent-v2` 形式 | ✅ |

### Step 2: Terraform dev 環境

| チェック項目 | 結果 |
|---|---|
| `terraform/environments/dev/variables.tf` が新規作成されている | ✅ |
| `region` のデフォルト値が `"asia-northeast1"` | ✅ |
| `terraform/environments/dev/main.tf` が新規作成されている | ✅ |
| `required_version = ">= 1.5"` が設定されている | ✅ |
| `google ~> 6.0` プロバイダが指定されている | ✅ |
| GCS バックエンド設定がコメントアウトで残されている | ✅ |
| `module "artifact_registry"` が `source = "../../modules/artifact_registry"` で呼び出されている | ✅ |
| `repository_id = "school-agent-dev"`, `environment = "dev"` が渡されている | ✅ |
| `terraform/environments/dev/outputs.tf` が新規作成されている | ✅ |
| `registry_url`, `image_base` がモジュール出力のパススルーとして定義されている | ✅ |

### Step 3: build_push.sh

| チェック項目 | 結果 |
|---|---|
| プロジェクトルートに `build_push.sh` が新規作成されている | ✅ |
| `chmod +x` で実行権限が付与されている (`-rwxr-xr-x`) | ✅ |
| `set -euo pipefail` が冒頭に設定されている | ✅ |
| 引数 `ENV`（default=`dev`）が実装されている | ✅ |
| 引数 `IMAGE_TAG`（default=git short SHA, fallback=`latest`）が実装されている | ✅ |
| `dev` → `school-agent-dev`, `prod` → `school-agent` の case 分岐がある | ✅ |
| 不明な ENV 値で `exit 1` するバリデーションがある | ✅ |
| `.env` から `PROJECT_ID` を読み込む（`deploy_v2.sh` と同じ方式） | ✅ |
| `PROJECT_ID` 未設定時に `exit 1` するチェックがある | ✅ |
| `uv export -o requirements.txt --no-hashes` が実行される | ✅ |
| `docker build -t "${IMAGE_URL}" .` が実行される | ✅ |
| `gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet` が実行される | ✅ |
| `docker push "${IMAGE_URL}"` が実行される | ✅ |
| 最終行に `IMAGE_URL=${IMAGE_URL}` が標準出力される | ✅ |

### Step 4: .gitignore 更新

| チェック項目 | 結果 |
|---|---|
| `terraform/**/terraform.tfstate` が追加されている | ✅ |
| `terraform/**/terraform.tfstate.backup` が追加されている | ✅ |
| `terraform/**/terraform.tfvars` が追加されている | ✅ |
| `terraform/**/.terraform/` は既存エントリ（`terraform/environments/**/.terraform/`）が存在するためスキップ | ✅（仕様通り） |

---

## テスト・静的解析結果

### terraform validate

```
$ cd terraform/environments/dev && terraform validate
Success! The configuration is valid.
```

**結果**: ✅ PASS

### build_push.sh 構文チェック

```
$ bash -n build_push.sh
syntax OK
```

**結果**: ✅ PASS

### 実行権限確認

```
$ ls -la build_push.sh
-rwxr-xr-x@ 1 masahiro  staff  1701  2 22 14:58 build_push.sh
```

**結果**: ✅ PASS

---

## 修正指示

なし（全要件を満たしており、テスト・静的解析もすべて PASS）。
