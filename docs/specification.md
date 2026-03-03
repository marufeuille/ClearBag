# ClearBag システム仕様書

> **注記**: 旧バッチシステム（school-agent v2 / Google Drive→Calendar/Todoist）の仕様は
> [docs/plan/commercialization-mvp.md](docs/plan/commercialization-mvp.md) 実装以前のものです。
> 現在のシステムは以下の B2C SaaS 仕様です。

---

## 1. 目的

学校・保育園から配布されるプリント（PDF・画像）をスマホで撮影・アップロードするだけで、
Gemini 2.5 Pro が内容を解析し、予定とタスクを自動抽出する B2C SaaS。

**コアバリュー**: 「撮って送るだけ」。保護者の代わりにお便りを読んで整理する AI 秘書。

---

## 2. ユーザーフロー

```
1. スマホで Firebase Auth（Google）ログイン
2. お便り PDF・写真をアップロード（ドラッグ&ドロップ / カメラ撮影）
3. 非同期で Gemini 2.5 Pro が解析（Cloud Tasks キュー）
4. 解析結果がカレンダー・タスクに反映される
5. iCal URL を Google カレンダー等に登録して自動同期
```

---

## 3. 機能要件

### 3.1 ドキュメント管理

| # | 機能 | 詳細 |
|---|---|---|
| F-01 | アップロード | PDF・JPG・PNG・WebP・HEIC 対応。最大ファイルサイズは GCS デフォルト |
| F-02 | 重複チェック | SHA-256 コンテンツハッシュで冪等性確保 |
| F-03 | 非同期解析 | Cloud Tasks → Worker（`/worker/analyze`）で非同期処理 |
| F-04 | ステータス管理 | `pending` → `processing` → `completed` / `error` |
| F-05 | 削除 | ドキュメント + 関連 events/tasks を Firestore から削除 |

### 3.2 AI 解析

| # | 機能 | 詳細 |
|---|---|---|
| F-10 | Gemini 呼び出し | Vertex AI Gemini 2.5 Pro（`gemini-2.5-pro`）|
| F-11 | 抽出項目 | サマリー・カテゴリー・イベント（日時・場所）・タスク（期限・担当者）|
| F-12 | confidence | HIGH / MEDIUM / LOW で信頼度を付与 |
| F-13 | カテゴリー | `EVENT` / `TASK` / `INFO` / `IGNORE` |
| F-14 | リトライ | tenacity で Vertex AI レート制限に対して指数バックオフリトライ |

### 3.3 カレンダー

| # | 機能 | 詳細 |
|---|---|---|
| F-20 | イベント一覧 | 日付範囲フィルター（`?from=YYYY-MM-DD&to=YYYY-MM-DD`）|
| F-21 | iCal フィード | トークンベース認証で認証不要の `.ics` エンドポイント |
| F-22 | iCal URL | Cloud Run URL（`https://clearbag-api-{env}.run.app/api/ical/{token}`）|

### 3.4 タスク管理

| # | 機能 | 詳細 |
|---|---|---|
| F-30 | タスク一覧 | 完了フィルター（`?completed=false`）|
| F-31 | 完了チェック | PATCH で `completed: true/false` を更新 |

### 3.5 プロファイル

| # | 機能 | 詳細 |
|---|---|---|
| F-40 | CRUD | 家族メンバー（名前・学年・キーワード）の登録・更新・削除 |
| F-41 | 解析精度向上 | プロファイルのキーワードを Gemini プロンプトに注入 |

### 3.6 ユーザー設定

| # | 機能 | 詳細 |
|---|---|---|
| F-50 | iCal トークン | 初回アクセス時に自動生成・Firestore に永続化 |
| F-51 | 解析枚数 | 今月の利用枚数を表示（無料プラン上限: 5枚）|

### 3.7 朝のダイジェスト

| # | 機能 | 詳細 |
|---|---|---|
| F-60 | スケジューラー | 毎朝 7:30 JST に Cloud Scheduler が `/worker/morning-digest` を呼び出し |
| F-61 | 通知内容 | 未完了タスク・今後7日間の予定を通知（SendGrid/WebPush、設定で ON/OFF）|

---

## 4. 非機能要件

### 4.1 プラン制限

| プラン | 月間解析枚数 |
|---|---|
| Free | 5枚 |
| Premium | 無制限（未実装） |

環境変数 `DISABLE_RATE_LIMIT=true` でスキップ可（dev 環境推奨）。

### 4.2 アクセス制御

- Firebase Authentication（Google Sign-in）で全 API を保護
- `ALLOWED_EMAILS` 環境変数でログイン可能アカウントを制限（空で全員許可）
- Cloud Tasks Worker は OIDC トークンで保護（Firebase Auth 不要）
- iCal エンドポイントはトークンベース（認証ヘッダー不要）

### 4.3 パフォーマンス

- アップロード API は 202 Accepted を即返し、解析は非同期（Cloud Tasks）
- Gemini のレート制限に合わせて Cloud Tasks キューを 1 rps / 同時3件に制限
- `COLLECTION_GROUP` スコープの Firestore 複合インデックスで横断クエリを高速化

### 4.4 インフラ

- **環境**: dev / prod を Terraform で完全管理
- **認証**: Workload Identity Federation（サービスアカウントキー不使用）
- **CI/CD**: main push → lint → test → Docker build → Terraform apply → Firebase Hosting deploy

---

## 5. データモデル（Firestore）

```
users/{uid}                               ← ユーザー設定（plan, ical_token 等）
users/{uid}/profiles/{profileId}          ← 家族プロファイル
users/{uid}/documents/{documentId}        ← ドキュメントレコード
users/{uid}/documents/{docId}/events/{eventId}  ← 抽出イベント（非正規化）
users/{uid}/documents/{docId}/tasks/{taskId}    ← 抽出タスク（非正規化）
```

### Firestore インデックス

イベント・タスクは `collection_group()` クエリで全ドキュメントをまたいで取得するため、
**`COLLECTION_GROUP` スコープ**の複合インデックスが必要。

| コレクション | フィールド | 用途 |
|---|---|---|
| `events` | `user_uid` ASC + `start` ASC | 日付範囲クエリ・iCal |
| `tasks` | `user_uid` ASC + `completed` ASC | 完了フィルタークエリ |

> **注意**: Terraform の `google_firestore_index` は `query_scope = "COLLECTION_GROUP"` の明示が必要。省略すると `COLLECTION` になり `collection_group()` クエリで 400 エラーになる。

---

## 6. API エンドポイント

| Method | Path | 認証 | 説明 |
|---|---|---|---|
| `POST` | `/api/documents/upload` | Firebase Auth | ファイルアップロード（202 Accepted）|
| `GET` | `/api/documents` | Firebase Auth | ドキュメント一覧 |
| `GET` | `/api/documents/{id}` | Firebase Auth | ドキュメント詳細 |
| `DELETE` | `/api/documents/{id}` | Firebase Auth | ドキュメント削除 |
| `GET` | `/api/events` | Firebase Auth | イベント一覧（日付範囲フィルター）|
| `GET` | `/api/tasks` | Firebase Auth | タスク一覧 |
| `PATCH` | `/api/tasks/{id}` | Firebase Auth | タスク完了状態更新 |
| `GET` | `/api/profiles` | Firebase Auth | プロファイル一覧 |
| `POST` | `/api/profiles` | Firebase Auth | プロファイル作成 |
| `PUT` | `/api/profiles/{id}` | Firebase Auth | プロファイル更新 |
| `DELETE` | `/api/profiles/{id}` | Firebase Auth | プロファイル削除 |
| `GET` | `/api/settings` | Firebase Auth | ユーザー設定取得 |
| `PATCH` | `/api/settings` | Firebase Auth | ユーザー設定更新 |
| `GET` | `/api/ical/{token}` | トークンのみ | iCal フィード（認証ヘッダー不要）|
| `POST` | `/worker/analyze` | OIDC | 解析ジョブ実行（Cloud Tasks から呼び出し）|
| `POST` | `/worker/morning-digest` | OIDC | 朝のダイジェスト送信（Cloud Scheduler から呼び出し）|
| `GET` | `/health` | なし | ヘルスチェック |

---

## 7. 環境変数

### バックエンド（Cloud Run / ローカル）

| 変数名 | 説明 | ローカルデフォルト |
|---|---|---|
| `PROJECT_ID` | GCP プロジェクト ID | 要設定 |
| `FIREBASE_PROJECT_ID` | Firebase プロジェクト ID | 要設定 |
| `GCS_BUCKET_NAME` | アップロード先 GCS バケット | `clearbag-local` |
| `CLOUD_TASKS_QUEUE` | Cloud Tasks キュー ID | — |
| `CLOUD_TASKS_LOCATION` | Cloud Tasks リージョン | — |
| `VERTEX_AI_LOCATION` | Vertex AI リージョン | `asia-northeast1` |
| `GEMINI_MODEL` | Gemini モデル名 | `gemini-2.5-pro` |
| `API_BASE_URL` | iCal URL 生成用ベース URL | `""` |
| `WORKER_URL` | Cloud Tasks が呼び出すワーカー URL | — |
| `SERVICE_ACCOUNT_EMAIL` | Cloud Tasks OIDC 用 SA メール | — |
| `ALLOWED_EMAILS` | ログイン許可メール（カンマ区切り）| `""` = 全員許可 |
| `DISABLE_RATE_LIMIT` | `true` で枚数制限スキップ | `true`（ローカル）|
| `LOCAL_MODE` | `true` で Cloud Tasks をスキップ | `true`（ローカル）|
| `CORS_ORIGINS` | 追加 CORS オリジン（カンマ区切り）| `""` |
| `FIRESTORE_EMULATOR_HOST` | Firestore エミュレーター | `localhost:8089` |
| `STORAGE_EMULATOR_HOST` | GCS エミュレーター | `http://localhost:4443` |

### フロントエンド（Next.js）

| 変数名 | 説明 |
|---|---|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase ウェブアプリの API キー |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase 認証ドメイン |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase プロジェクト ID |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase Storage バケット |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase Messaging Sender ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase アプリ ID |
| `NEXT_PUBLIC_API_BASE_URL` | バックエンド API URL（ローカル: `http://localhost:8000`）|
