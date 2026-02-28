# Terraform Plan CI ワークフロー実装プラン

## Context

PR に Terraform の変更が含まれる場合、`terraform plan` の結果を dev/prod それぞれ PR コメントとして自動表示する CI ワークフローを追加する。レビュアーが PR 画面でインフラ変更の影響範囲を確認できるようになり、意図しない変更の早期検知が可能になる。

## 調査結果まとめ

- **クラウド**: GCP
- **Terraform state**: GCS バケット `clearbag-dev-terraform-backend` (dev) / `clearbag-prod-terraform-backend` (prod)
- **認証**: Workload Identity Federation (`google-github-actions/auth@v2`)
  - dev: `environment: dev` に `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT` が設定済み
  - prod: `environment: prod` に `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT` が設定済み（保護ルールなし）
- **既存ワークフロー**: `.github/workflows/ci.yml`, `cd-dev.yml`, `cd-prod.yml`
- **Terraform 環境**: `terraform/environments/dev/`, `terraform/environments/prod/`
- **terraform.tfvars**: dev/prod ともに全変数が定義済み（plan 時は `-var` フラグ不要）

## 作成ファイル

| ファイル | 種別 |
|---------|------|
| `.github/workflows/tf-plan.yml` | 新規作成（メイン成果物） |

## ワークフロー設計

### ファイルパス

```
.github/workflows/tf-plan.yml
```

### トリガー

```yaml
on:
  pull_request:
    branches: [main]
    paths:
      - 'terraform/**'
```

Terraform ファイル以外の変更（Python コードなど）ではトリガーしない。

### 権限

```yaml
permissions:
  id-token: write      # WIF OIDC トークン発行
  contents: read       # チェックアウト
  pull-requests: write # PR コメント投稿
```

### ジョブ構成（dev/prod 並列実行）

```
plan-dev  ─┐
            ├── 並列実行
plan-prod ─┘
```

### 各ジョブの手順

| ステップ | アクション / コマンド |
|---------|---------------------|
| チェックアウト | `actions/checkout@v4` |
| GCP 認証 | `google-github-actions/auth@v2` (既存 CD パターンと同一) |
| Terraform セットアップ | `hashicorp/setup-terraform@v3` |
| `terraform init` | `working-directory: terraform/environments/{env}` |
| `terraform plan` | `-no-color 2>&1 \| tee plan.txt` |
| PR コメント投稿 | `actions/github-script@v7` |

### Terraform 変数の扱い

`terraform.tfvars` に全変数が定義済みのため、plan CI では追加の `-var` フラグなしで実行可能。

```bash
terraform plan -no-color 2>&1 | tee plan.txt
```

> `image_url` は tfvars の `latest` タグが使われるが、インフラ差分確認の目的上は問題なし。

### PR コメント形式

```markdown
<!-- tf-plan-dev -->
## Terraform Plan - dev

<details>
<summary>プラン結果（クリックで展開）</summary>

```hcl
No changes. Your infrastructure matches the configuration.
（または差分内容）
```

</details>

**ステータス**: ✅ 成功 / ❌ 失敗
**実行日時**: 2024-01-01 00:00:00 UTC
**コミット**: abc1234
```

### コメント更新戦略

識別マーカー `<!-- tf-plan-dev -->` / `<!-- tf-plan-prod -->` を埋め込み、`actions/github-script@v7` で既存コメントを検索して更新。同一 PR への複数コミットでコメントが増殖しない。

65,000 文字超の場合は末尾を切り捨て（GitHub コメント上限への対策）。

### ワークフロー全体像（擬似 YAML）

```yaml
name: Terraform Plan

on:
  pull_request:
    branches: [main]
    paths:
      - 'terraform/**'

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  plan-dev:
    name: Plan (dev)
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      - uses: hashicorp/setup-terraform@v3
      - name: Terraform Init
        working-directory: terraform/environments/dev
        run: terraform init
      - name: Terraform Plan
        id: plan
        working-directory: terraform/environments/dev
        run: terraform plan -no-color 2>&1 | tee plan.txt
        continue-on-error: true
      - name: Post PR Comment
        uses: actions/github-script@v7
        with:
          script: |
            # plan.txt を読み込み、65000文字で切り捨て
            # <!-- tf-plan-dev --> マーカーで既存コメントを検索・更新

  plan-prod:
    name: Plan (prod)
    runs-on: ubuntu-latest
    environment: prod
    steps:
      # plan-dev と同様（ディレクトリを prod に変更）
```

## 検証方法

1. `terraform/` 配下のファイルを編集して PR を作成
2. Actions タブで `Terraform Plan` ワークフローが起動することを確認
3. `plan-dev` / `plan-prod` ジョブが並列実行されることを確認
4. PR コメントに dev/prod それぞれの計画結果が投稿されることを確認
5. 追加コミットを push した際、コメントが新規追加ではなく更新されることを確認
6. Python コードのみの変更では tf-plan ワークフローが起動しないことを確認
7. Terraform 変更がない（`No changes`）ケースでもコメントが投稿されることを確認
