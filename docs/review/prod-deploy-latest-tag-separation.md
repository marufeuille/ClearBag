# レビューレポート: prod-deploy-latest-tag-separation

- **レビュー日時**: 2026-02-23
- **全体ステータス**: ✅ PASS

---

## 要件カバレッジ

### 目標

| # | 要件 | 結果 |
|---|---|---|
| 1 | Cloud Run Job のイメージ参照を常に `latest-prod` タグに固定する | ✅ |
| 2 | コンテナビルド/プッシュと Terraform デプロイを別ワークフローに分離する | ✅ |
| 3 | ロールバック機能を維持する | ✅ |
| 4 | `tf-cmt-prod.yml`（PR 時の terraform plan）との整合性を保つ | ✅ |

---

### トリガー一覧の実装確認

| ワークフロー | トリガー | 仕様 | 実装 |
|---|---|---|---|
| `cd-prod-build.yml` | `push` (tags: `v*`) | ✅ | ✅ |
| `cd-prod-build.yml` | `workflow_dispatch` (target_tag) | ✅ | ✅ |
| `cd-prod-terraform.yml` | `workflow_run` (build 完了後) | ✅ | ✅ |
| `cd-prod-terraform.yml` | `push` (main, terraform/** 変更) | ✅ | ✅ |
| `cd-prod-terraform.yml` | `workflow_dispatch` | ✅ | ✅ |

---

### 詳細チェックリスト

#### cd-prod-build.yml

- [x] `name: Build & Push Prod Image` — `cd-prod-terraform.yml` の `workflow_run` 参照と完全一致
- [x] `lint` / `test` ジョブに `if: github.event_name == 'push'` — ロールバック時スキップ
- [x] `build-push` の `if: always() && (needs.lint.result == 'success' || 'skipped') && ...` — skipped 依存への正しい対処
- [x] 通常デプロイ: SHA タグ / release タグ / `latest-prod` タグの 3 種を push
- [x] ロールバック: 対象タグの存在確認 → `latest-prod` として re-tag → push
- [x] `environment: prod` + `concurrency: group: build-prod` — 並行実行防止
- [x] Docker コンテキストに Terraform 操作なし（疎結合を達成）

#### cd-prod-terraform.yml

- [x] `workflow_run: workflows: ["Build & Push Prod Image"]` — ワークフロー名が正確に一致
- [x] `if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'` — ビルド失敗時の Terraform apply をガード
- [x] `terraform apply` に `-var="image_url=..."` の CLI 引数なし — `terraform.tfvars` から自動読み込み
- [x] `environment: prod` + `concurrency: group: deploy-prod` — 並行実行防止
- [x] Terraform コンテキストに Docker/イメージ操作なし（疎結合を達成）

#### terraform/environments/prod/terraform.tfvars

- [x] `image_url` が `...school-agent-v2:latest-prod` に更新済み
- [x] 旧値 `...school-agent-v2:latest` を完全に置換
- [x] コメントが更新され、ファイル内で意図が自己説明されている

#### tf-cmt-prod.yml

- [x] `terraform plan` の `image_url` が `prod-latest` → `latest-prod` に変更済み
- [x] CD の apply と同じ `image_url` を参照するため整合性が保たれている

#### 削除・不変ファイル

- [x] `.github/workflows/cd-prod.yml` — 削除済み
- [x] `cd-dev.yml` — 変更なし
- [x] `terraform/modules/` — 変更なし
- [x] `terraform/environments/prod/main.tf` — 変更なし

---

## テスト・静的解析結果

### Ruff（Lint/Format）

```
$ uv run ruff check v2/
$ uv run ruff format --check v2/
All checks passed!
21 files already formatted
```

**結果: PASS**

### pytest（単体・統合テスト）

```
$ uv run pytest tests/unit/ tests/integration/ -m "not manual" --tb=short -q

collected 40 items / 3 deselected / 37 selected

tests/unit/test_action_dispatcher.py ..........  [ 27%]
tests/unit/test_credentials.py ......            [ 43%]
tests/unit/test_models.py .............          [ 78%]
tests/unit/test_orchestrator.py ........         [100%]

37 passed, 3 deselected in 0.33s
```

**結果: PASS**

### YAML 構文チェック

```
YAML OK: .github/workflows/cd-prod-build.yml
YAML OK: .github/workflows/cd-prod-terraform.yml
YAML OK: .github/workflows/tf-cmt-prod.yml
```

**結果: PASS**

### 旧タグ参照の残留チェック

```
$ grep -r 'prod-latest' .github/workflows/ terraform/
→ 0 件（残留なし）
```

**結果: PASS**

### workflow_run 名前整合性

```
cd-prod-build.yml  name: "Build & Push Prod Image"
cd-prod-terraform.yml  workflow_run.workflows: ["Build & Push Prod Image"]
→ 完全一致
```

**結果: PASS**

---

## 特記事項（情報提供）

以下は修正を要するものではなく、運用上の留意点として記録する。

1. **初回移行時の前提条件**: `latest-prod` タグが Artifact Registry に存在しない状態で `cd-prod-terraform.yml` が走ると Terraform apply が失敗する。仕様書の「移行計画」に手順が明記されており、実装上の問題ではない。

2. **`workflow_run` の動作制約**: `cd-prod-terraform.yml` は **デフォルトブランチ（main）のコード** で実行される。これは GitHub Actions の仕様であり、実装上の問題ではない。仕様書に明記済み。

3. **`tf-cmt-prod.yml` での image_url 二重指定**: `terraform.tfvars` に `latest-prod` が書かれているため、`tf-cmt-prod.yml` で `-var="image_url=..."` を渡すのは技術的には冗長だが、明示的であり仕様書でも明記された変更であるため問題なし。

---

## 修正指示

なし（全要件を満たしており、テスト・静的解析も全 PASS）
