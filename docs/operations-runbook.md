# ClearBag 運用ランブック

運用で頻繁に使うコマンド・ワークフローの一覧。

## 環境 URL

| 環境 | フロントエンド | バックエンド API |
|---|---|---|
| dev | https://clearbag-dev.firebaseapp.com/ | Cloud Run (dev) |
| prod | https://clearbag-prod.firebaseapp.com/ | Cloud Run (prod) |

---

## 1. 新規ユーザーをサービスに招待する

### 1-A. サービス招待コードで招待（メールアドレス不要・複数人共有可）

```bash
# dev 環境（デフォルト）
PROJECT_ID=clearbag-dev uv run python scripts/create_service_code.py \
  --expires-in-days 30 \
  --max-uses 50 \
  --description "友人招待用"

# prod 環境（--frontend-url を明示指定）
PROJECT_ID=clearbag-prod uv run python scripts/create_service_code.py \
  --expires-in-days 30 \
  --max-uses 50 \
  --description "友人招待用" \
  --frontend-url https://clearbag-prod.firebaseapp.com
```

出力例：
```
Created service code: A3kX9mP2
Invite URL: https://clearbag-dev.firebaseapp.com/register?code=A3kX9mP2
Expires: 2026-04-07T09:00:00+09:00
Max uses: 50
```

生成された `Invite URL` を相手に共有するだけ。
相手は Google でサインイン → 自動でアクティベート → ダッシュボードへ。

**オプション一覧:**

| オプション | 必須 | 説明 |
|---|---|---|
| `--expires-in-days` | ✅ | 有効期限（日数） |
| `--max-uses` | | 利用上限（省略時は無制限） |
| `--code` | | コード文字列（省略時はランダム8文字） |
| `--description` | | メモ用の説明文 |
| `--frontend-url` | | URL プレフィックス（省略時: dev URL） |

### 1-B. ファミリー内招待（メールアドレス指定・同じファミリーに追加）

ダッシュボードの設定ページ → ファミリー管理 → 「メンバーを招待」から実施。
招待先のメールアドレスが必要。招待を受けた側は `/invite?token=...` でファミリーに参加する。

### 1-C. コードの管理（一覧・revoke）

```bash
# 一覧表示
PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py list

# コードを即時無効化
PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py revoke A3kX9mP2

# dry-run で確認
PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py revoke A3kX9mP2 --dry-run
```

---

## 2. 既存ユーザーを手動でアクティベートする

メール指定（Firebase Auth にアカウントがある場合）:
```bash
PROJECT_ID=clearbag-dev uv run python scripts/activate_existing_users.py \
  --email user@example.com
```

UID 直接指定:
```bash
PROJECT_ID=clearbag-dev uv run python scripts/activate_existing_users.py \
  --uid <firebase-uid>
```

全ユーザー一括（変更前に `--dry-run` で確認推奨）:
```bash
PROJECT_ID=clearbag-dev uv run python scripts/activate_existing_users.py --dry-run
PROJECT_ID=clearbag-dev uv run python scripts/activate_existing_users.py
```

---

## 3. ユーザーを停止する

サービスへのアクセスを即時ブロックする（次回APIアクセスで403）。

```bash
# メールアドレスで指定
PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --email user@example.com

# UID で指定
PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --uid <uid>

# dry-run で確認してから実行
PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --email user@example.com --dry-run
```

停止を解除するには `activate_existing_users.py` を使う。

---

## 4. dev 環境データのリセット

```bash
PROJECT_ID=clearbag-dev uv run python scripts/reset_dev_data.py --email you@gmail.com
```

Firestore と GCS を初期化し、指定メールのユーザーにデモデータをシードする。

---

## 5. Firestore セキュリティルールの検証

```bash
bash scripts/test_firestore_rules.sh
```

---

## 6. Worker エンドポイントの OIDC 認証検証

```bash
bash scripts/verify_worker_auth.sh [BASE_URL]
```

---

## 7. prod リリース

```bash
git tag v1.x.x
git push origin v1.x.x
```

`cd-prod-build.yml` → Docker ビルド → `cd-prod-terraform.yml` → Terraform apply (prod) の順に自動実行。
