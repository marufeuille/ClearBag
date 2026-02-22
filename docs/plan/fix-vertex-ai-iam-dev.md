# IAM 修正: Vertex AI 呼び出し権限の付与（dev 環境）

## Context

Cloud Run Job の実行 SA（`school-agent-v2-dev`）が Vertex AI（Gemini）を呼び出した際に以下のエラーが発生：

```
403 Permission 'aiplatform.endpoints.predict' denied on resource
  '//aiplatform.googleapis.com/projects/marufeuille-linebot/locations/us-central1/publishers/google/models/gemini-2.5-pro'
```

### 原因

`terraform/environments/dev/main.tf` で `google_service_account "cloud_run"` を Terraform で新規作成したが、**プロジェクトレベルの Vertex AI 呼び出し権限**が付与されていない。

アプリは Cloud 環境（`CLOUD_RUN_JOB` 環境変数）を検出すると `google.auth.default()` で ADC を使用する。ADC は SA のトークンを取得するが、**SA に `aiplatform.endpoints.predict` 権限がなければ 403 が発生**する。

### 現状の IAM 設定（不足している権限）

| 役割 | 対象リソース | 付与方法 | 状態 |
|---|---|---|---|
| `roles/secretmanager.secretAccessor` | 各 Secret | `secret_manager` module | ✅ 付与済み |
| `roles/run.invoker` | Cloud Run Job | `cloud_run_job` module | ✅ 付与済み |
| `roles/aiplatform.user` | プロジェクト | — | ❌ **未付与** |

---

## 変更対象ファイル

| ファイル | 操作 | 変更内容 |
|---|---|---|
| `terraform/environments/dev/main.tf` | **修正** | `google_project_iam_member` を追加 |

---

## 実装仕様

### `terraform/environments/dev/main.tf`

Service Account 定義の直後に、プロジェクトレベルの IAM バインディングを追加する:

```hcl
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}
```

- リソース名: `vertex_ai_user`（役割を明示）
- `roles/aiplatform.user`: Vertex AI モデルへの predict 呼び出しを許可する最小権限ロール
- `google_service_account.cloud_run.email` を参照（ハードコードしない）

---

## 検証手順

```bash
# Terraform 構文チェック
cd terraform/environments/dev
terraform validate
```

---

## 補足：他の Google サービスの IAM について

Drive / Sheets / Calendar はプロジェクト IAM ではなく、**リソースの共有設定**（Drive フォルダ・スプレッドシートを SA のメールアドレスに共有）で動作するため、本修正のスコープ外とする。

Todoist・Slack は Bearer Token 認証のため IAM 不要。
