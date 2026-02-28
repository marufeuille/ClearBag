# アップロードバリデーション 手動検証ガイド

Issue #64 で追加したファイルサイズ・PDF ページ数制限が、デプロイ後の dev 環境で
正常に動作しているかを確認するための手順書。

---

## 検証シナリオ

| # | シナリオ | 使用ファイル | 期待レスポンス |
|---|---------|------------|-------------|
| 1 | 通常 PDF（1ページ） | `fixtures/valid_1page.pdf` | **202** Accepted |
| 2 | サイズ超過（11MB） | スクリプト内で生成 | **413** Too Large |
| 3 | ページ数超過（4ページ） | `fixtures/over_limit_4page.pdf` | **422** Unprocessable |
| 4 | 破損 PDF | `fixtures/corrupted.pdf` | **422** Unprocessable |

> **注意**: デフォルトのページ数上限は **3ページ**、サイズ上限は **10MB**。
> 環境変数 `MAX_PDF_PAGES` / `MAX_UPLOAD_SIZE_MB` で変更可能。

---

## 事前準備

### 1. Firebase ID トークンの取得

トークンは **1時間** で失効するので、検証直前に取得すること。

このアプリは Firebase SDK v9（モジュール型）を使っており、`firebase` グローバル変数は
存在しない。**Network タブから取得するのが最も確実**。

#### Network タブから取得（推奨）

1. dev 環境のアプリをブラウザで開き、ログインする
2. DevTools を開く（F12）→ **Network** タブ
3. ダッシュボードなど `/api/` へのリクエストが発生するページに移動する
4. Network タブの一覧から `/api/documents` や `/api/families/me` などのリクエストをクリック
5. **Headers** タブ → **Request Headers** セクションの `Authorization` 行を確認
6. `Bearer eyJhbGci...` の `Bearer ` より後をコピーする（`eyJ` で始まる長い文字列）

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtp...  ← ここの Bearer 以降をコピー
```

#### Console から取得（代替手段）

Firebase SDK v9 のモジュールは console から直接アクセスできないが、
以下のように Next.js の内部モジュールを経由することで取得できる場合がある:

```javascript
// ダッシュボードのページで試す（動作は Next.js のバンドル構成に依存）
const { auth } = await import("/_next/static/chunks/src_lib_firebase_ts.js");
await auth.currentUser?.getIdToken();
```

> **それでも取れない場合**: Network タブの方法を使う。Console アプローチは
> バンドルのキャッシュ名が変わると使えなくなる。

### 2. API URL の確認

Cloud Run サービスの URL を確認する:

```bash
gcloud run services describe clearbag-api-dev \
  --region asia-northeast1 \
  --project clearbag-dev \
  --format "value(status.url)"
```

---

## スクリプトによる自動検証

```bash
# dev 環境に対して実行
API_URL=https://api-xxxxxxxxxx-an.a.run.app \
FIREBASE_TOKEN=eyJhbGciO... \
uv run python tests/manual/test_upload_validation.py
```

### 期待される出力

```
=======================================================
  アップロードバリデーション 手動検証
=======================================================
  API_URL     : https://api-xxxxxxxxxx-an.a.run.app
  USE_FIXTURES: False
  token       : eyJhbGciOiJSUzI1Ni...
=======================================================

[1/4] 通常 PDF (1ページ, ~1KB) → 202 期待
  ✅ status=202  期待=202
     → doc_id=xxxxxxxx-xxxx を削除しました（クリーンアップ）

[2/4] サイズ超過 (11MB) → 413 期待
  （11MB ダミーファイルをメモリ上で生成中...）
  ✅ status=413  期待=413

[3/4] ページ数超過 (4ページ) → 422 期待
  ✅ status=422  期待=422

[4/4] 破損 PDF → 422 期待
  ✅ status=422  期待=422

=======================================================
  ✅ 全シナリオ通過: 4/4
=======================================================
```

### 失敗した場合

シナリオ 2〜4 が **202 を返している** 場合 → バリデーション実装がデプロイされていない可能性。
Cloud Run のイメージバージョンを確認:

```bash
gcloud run services describe clearbag-api-dev \
  --region asia-northeast1 \
  --project clearbag-dev \
  --format "value(spec.template.spec.containers[0].image)"
```

### オプション

```bash
# fixtures/ の実ファイルを使いたい場合
USE_FIXTURES=1 API_URL=... FIREBASE_TOKEN=... uv run python tests/manual/test_upload_validation.py

# シナリオ1で登録されたドキュメントを削除しない場合
DISABLE_CLEANUP=1 API_URL=... FIREBASE_TOKEN=... uv run python tests/manual/test_upload_validation.py
```

---

## ブラウザ UI での手動確認

`fixtures/` に UI でドラッグ&ドロップして確認できるファイルを用意している。

| ファイル | 使い方 |
|---------|--------|
| `fixtures/valid_1page.pdf` | 通常アップロード → 成功することを確認 |
| `fixtures/valid_3page.pdf` | ページ数上限ぴったり → 成功することを確認 |
| `fixtures/over_limit_4page.pdf` | ページ数超過 → エラーメッセージ表示を確認 |
| `fixtures/corrupted.pdf` | 破損ファイル → エラーメッセージ表示を確認 |

> **11MB 超のファイル確認**: ブラウザで大きなファイルを試すには、以下で生成したものを使う:
> ```bash
> # 11MB のダミーファイルを生成（git には含めない）
> python -c "open('tests/manual/fixtures/over_limit_11mb.bin', 'wb').write(b'\\x00' * (11 * 1024 * 1024))"
> ```
> クライアント側でブロックされるため、サーバーにリクエストは飛ばない。

---

## デプロイ前後の挙動比較

| | デプロイ前（旧コード） | デプロイ後（新コード） |
|--|---------------------|---------------------|
| 11MB PDF | 202（制限なし） | **413** |
| 4ページ PDF | 202（制限なし） | **422** |
| 破損 PDF | 202 or 500 | **422** |

> **「今やると全部通っちゃう」** のはこのため。デプロイ後に実行すること。
