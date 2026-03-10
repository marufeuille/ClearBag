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
# 一覧表示（dev）
PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py list

# 一覧表示（prod）
PROJECT_ID=clearbag-prod uv run python scripts/manage_service_codes.py list

# コードを即時無効化
PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py revoke A3kX9mP2

# dry-run で確認してから revoke
PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py revoke A3kX9mP2 --dry-run
```

list 出力例：
```
CODE       DESCRIPTION   USED  MAX  REMAINING  EXPIRES           STATUS
A3kX9mP2  友人招待用       3     50   47         2026-04-07 09:00  active
B9zQ1rT5  テスト用         5     5    0          2026-03-01 00:00  exhausted
C4mW7yK1  期限切れ         1     10   9          2026-02-01 00:00  expired
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

サービスへのアクセスを即時ブロックする（次回APIアクセスで403 ACTIVATION_REQUIRED）。

```bash
# メールアドレスで指定（dev）
PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --email user@example.com

# メールアドレスで指定（prod）
PROJECT_ID=clearbag-prod uv run python scripts/deactivate_user.py --email user@example.com

# UID で直接指定
PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --uid <firebase-uid>

# dry-run で確認してから実行
PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --email user@example.com --dry-run
```

停止を解除（再アクティベート）するには `activate_existing_users.py` を使う（セクション2参照）。

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

## 7. Gemini 抽出フィクスチャの録画（extras テスト用）

`tests/fixtures/gemini_responses/` には、Gemini が返す JSON レスポンスのサンプルが保存されている。
新しい PDF パターン（サマーフェスタのお知らせ・修学旅行など）を追加するときや、
Gemini モデルのバージョンアップ後に抽出品質を確認したいときに録画を実施する。

### 7-A. 新しいパターンを録画する

```bash
# 1. 実 Gemini API を呼び出してレスポンスを保存する
PROJECT_ID=clearbag-dev \
uv run pytest tests/unit/test_gemini_extras_fixture.py::TestRecordGeminiResponse \
    -m manual -v -s \
    --pdf-path=path/to/sample.pdf \
    --fixture-name=my_new_fixture
```

実行後、`tests/fixtures/gemini_responses/my_new_fixture.json` が生成される。
コンソール出力に抽出された items・costs・notes が表示されるので内容を確認する。

```bash
# 2. 期待値ファイルを手書きで作成する
# tests/fixtures/expectations/my_new_fixture.json
{
  "description": "このフィクスチャの説明",
  "extras": {
    "must_contain_items": ["水筒", "お弁当"],        # 絶対含まれるべき持ち物
    "must_contain_dress_code_keywords": ["体操服"],  # 部分一致で確認
    "costs": [
      {
        "description_contains": "遠足",             # 費用名に含まれるキーワード
        "amount_range": [400, 600],                 # 金額の許容範囲
        "due_date_prefix": "2026-04"                # 期限の年月プレフィックス
      }
    ],
    "must_contain_note_keywords": ["雨天"]           # 注意事項の部分一致
  }
}
```

期待値は「完全一致」ではなく「含んでいること」の宣言で書く。
Gemini の出力の揺れ（"水筒（500ml以上）" など）に対してもテストが壊れないようにするため。

```bash
# 3. _FIXTURE_NAMES に追加して CI に組み込む
# tests/unit/test_gemini_extras_fixture.py の先頭付近にあるリストに追記する
_FIXTURE_NAMES = [
    "excursion_notice",
    "cost_notice",
    "schedule_only",
    "my_new_fixture",   # ← 追加
]
```

### 7-B. モデルバージョンアップ後の再録画

Gemini のモデルを変更したとき（例: `gemini-2.5-pro` → 新バージョン）は、
既存フィクスチャを上書き録画して期待値との整合性を確認する。

```bash
# 既存フィクスチャを上書き（同じ --fixture-name を指定）
PROJECT_ID=clearbag-dev \
uv run pytest tests/unit/test_gemini_extras_fixture.py::TestRecordGeminiResponse \
    -m manual -v -s \
    --pdf-path=tests/fixtures/source_pdfs/excursion_notice.pdf \
    --fixture-name=excursion_notice

# 上書き後に通常テストが通ることを確認
uv run pytest tests/unit/test_gemini_extras_fixture.py -m "not manual" -v
```

### 7-C. フィクスチャのファイル構成

```
tests/
├── fixtures/
│   ├── gemini_responses/       # 録画済み Gemini レスポンス JSON（git 管理）
│   │   ├── excursion_notice.json   遠足（持ち物・服装・費用・注意）
│   │   ├── cost_notice.json        集金（複数費用）
│   │   └── schedule_only.json      行事予定のみ（extras なし）
│   ├── expectations/           # 期待値宣言 JSON（git 管理）
│   │   ├── excursion_notice.json
│   │   ├── cost_notice.json
│   │   └── schedule_only.json
│   └── source_pdfs/            # 録画元 PDF（git 管理外・.gitignore 推奨）
└── unit/
    └── test_gemini_extras_fixture.py
```

---

## 8. prod リリース

```bash
git tag v1.x.x
git push origin v1.x.x
```

`cd-prod-build.yml` → Docker ビルド → `cd-prod-terraform.yml` → Terraform apply (prod) の順に自動実行。
