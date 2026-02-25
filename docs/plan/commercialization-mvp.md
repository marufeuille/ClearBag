# ClearBag 商用化検討: B2C MVP アーキテクチャ設計

> 作成日: 2026-02-24
> ステータス: 方針確定・実装前

---

## 1. 背景・目的

ClearBag は現在「1家庭=1デプロイ」の個人用ツールとして稼働している。これを不特定多数の保護者が使える SaaS として商用化する際の、アーキテクチャの進化方向を検討した議論の記録。

**現状の価値の核:** `Google Drive のPDF → Gemini 2.5 Pro → Google Calendar / Todoist / Slack` という自動化パイプライン。最も重要な価値は **「配布物から構造化データを取り出す AI 解析部分」** であり、Google Drive/Calendar 等の外部サービスはあくまで入出力チャネルに過ぎない。

---

## 2. 現状のアーキテクチャ分析

### シングルテナント設計の課題

現在は全リソースが環境変数で 1 セット固定されており、マルチテナント化のためには全レイヤーで再設計が必要。

| 課題 | 影響箇所 |
|------|---------|
| `AppConfig` に全テナント設定が 1 セット | `v2/config.py` |
| `lru_cache(maxsize=1)` でGoogle認証情報がプロセスで 1 つ | `v2/adapters/credentials.py` |
| `vertexai.init()` がコンストラクタでグローバル初期化 | `v2/adapters/gemini.py:55` |
| 処理結果 (DocumentAnalysis) が永続化されない | `v2/services/orchestrator.py` |
| ページネーション未実装 (pageSize=100 で止まる) | `v2/adapters/google_drive.py` |
| リトライ/レート制限対策なし | 全アダプター |

### 再利用可能な資産

Hexagonal Architecture が既に適用されており、Port/Adapter の分離が商用化の土台になる。

| コンポーネント | 再利用度 | 内容 |
|---|---|---|
| `v2/domain/models.py` の各モデル | **高** | `DocumentAnalysis`, `EventData`, `TaskData` はそのまま使える |
| `v2/domain/ports.py` の ABC 群 | **高** | 新 Adapter の土台として活用。拡張して使う |
| `v2/adapters/gemini.py` のプロンプト・解析ロジック | **高** | 行 148-304 のプロンプト構築 + レスポンスパースは 100% 再利用可能 |
| `v2/services/orchestrator.py` の `_process_single` | **中** | 1ファイル処理のコアロジック。独立サービスとして抽出できる |
| `v2/logging_config.py` | **高** | Cloud Run 環境判定ロジックがそのまま使える |

---

## 3. 競合分析

### 学校発 B2B プラットフォーム（知性なし）

既存の学校連絡ツールは **配信チャネルのデジタル化** に止まっている。

| サービス | やっていること | やっていないこと |
|---|---|---|
| [スクリレ](https://www.sukurire.jp/) | お便りPDF配信、欠席連絡、アンケート、面談調整 (2026年新機能) | **カレンダー連携、行事抽出、持ち物リマインダー** |
| [テトル](https://tetoru.jp/) | 連絡配信、欠席連絡、校務支援連携 | **カレンダー連携、構造化データ抽出** |

**重要な観察:** これらは「学校が導入してくれて初めて使えるもの」。保護者が今すぐ自分で使い始めることはできない。また、紙をPDFにしているだけで、中身の解釈は保護者の手作業のまま。

### 保護者側 B2C ツール

| サービス | やっていること | やっていないこと |
|---|---|---|
| [おたよりBOX](https://ict-enews.net/2016/05/20nifty/) | 写真整理、手動カレンダー設定、アラート通知 (¥500/月) | **AI 自動抽出** ─ 日付もイベントも手動入力 |
| [TimeTree](https://kosodate-update.com/timetree-otayori-calendar/) | **画像読み取りで予定を自動登録** | 学校特化ではない。タスク・持ち物抽出なし |

**TimeTree が最大の競合。** ただし汎用カレンダーアプリの 1 機能に過ぎず、学校配布物への特化度は低い。

### ClearBag の差別化ポイント

| 観点 | TimeTree | ClearBag (商用版) |
|---|---|---|
| 本業 | 汎用共有カレンダー | 学校配布物に特化 |
| 抽出対象 | 日付・時間のみ | **イベント + 持ち物 + タスク + カテゴリ** |
| 理解の深さ | 汎用OCR+AI | 学校文脈に特化したプロンプト設計 |
| 複数ページ対応 | 1枚ずつ | 複数ページの文書を一括解析 |
| 出力先 | カレンダーのみ | カレンダー + タスク + リマインダー + iCal |

---

## 4. 方針決定

### 選んだ戦略: B2C MVP → B2B ピボット

**B2C から始める理由:**
1. 「保護者は本当にこれにお金を払うか？」を最小コストで市場検証できる
2. B2C のトラクション（利用者数）が B2B 営業のカードになる（「この学校の保護者が○○人使っています」）
3. 既存の Hexagonal Architecture を活かして最小の変更で実現できる
4. B2B への進化パスが自然（「同じ学校の保護者が多い」→ 学校に営業）

### 確定した要件

| 項目 | 決定内容 |
|---|---|
| ターゲット顧客 | **個人（保護者）向け B2C** |
| Google Workspace 依存 | **排除**（ユーザー側は Drive/Sheets/Calendar 不要） |
| 入力方法 | **PWA（Web App）** でカメラ撮影 / PDF アップロード |
| 出力方法 | **Web ダッシュボード** + **iCal フィード** + Email/Web Push 通知 |
| 課金モデル | **フリーミアム**（月5枚無料 / ¥300/月で無制限）※ MVP では実装後回し |
| インフラ | **GCP に残す**（Vertex AI Gemini との親和性） |

---

## 5. ターゲットアーキテクチャ

### コンポーネント構成

```
[保護者]
   │ カメラ撮影 / PDF アップロード
   ↓
[PWA] ← Firebase Hosting (Next.js, オフラインシェル対応)
   │ Firebase Auth (ID Token)
   ↓
[Cloud Run Service] ← FastAPI (REST API)
   │
   ├─→ [Cloud Storage]    : ファイル保存
   ├─→ [Cloud Tasks]      : 非同期解析キュー
   └─→ [Firestore]        : データ永続化
               │
               ↓
        [Cloud Run Worker]
               │
               ↓
        [Vertex AI Gemini 2.5 Pro]  ← 現在の GeminiDocumentAnalyzer 再利用
               │
               ↓
        [Firestore] ← 解析結果を永続化
               │
   ┌───────────┼───────────┐
   ↓           ↓           ↓
[Web UI]   [iCal Feed]  [Email/Web Push]
```

### データフロー

**アップロード:**
```
1. POST /api/documents/upload (multipart/form-data)
2. ファイル → Cloud Storage に保存
3. Firestore に DocumentRecord (status=pending) を作成
4. Cloud Tasks にキューイング
5. 202 Accepted をユーザーに返す (即レスポンス)

6. [非同期] Worker: Cloud Tasks から受信
7. Cloud Storage からファイルをダウンロード
8. Firestore からユーザーのプロファイル・ルールを取得
9. GeminiDocumentAnalyzer.analyze() を実行
10. 解析結果を Firestore に保存 (status=completed)
11. ユーザーに Email/Web Push 通知
```

**閲覧:**
```
GET /api/events?from=2026-03-01&to=2026-03-31
→ Firestore users/{uid}/events からクエリ
→ JSON レスポンス

GET /api/ical/{token} (認証不要)
→ icalToken で users コレクションからユーザー特定
→ events から iCal 形式のテキストを生成してレスポンス
```

### Firestore データモデル

```
users/{uid}
  ├── plan: "free" | "premium"
  ├── documentsThisMonth: number         # 無料枠チェック用
  ├── icalToken: string                  # UUID, iCal フィードアクセス用
  ├── notificationPreferences: map
  │   ├── email: boolean
  │   └── webPush: boolean
  └── webPushSubscription: map

users/{uid}/profiles/{profileId}
  ├── name: string     # 例: "太郎"
  ├── grade: string    # 例: "小3"
  └── keywords: string # 例: "サッカー,遠足"
  (calendar_id は不要: カレンダーは ClearBag が内部管理)

users/{uid}/documents/{documentId}
  ├── status: "pending" | "processing" | "completed" | "error"
  ├── contentHash: string    # SHA-256 ── 冪等性チェックのキー
  ├── storagePath: string    # GCS: "uploads/{uid}/{documentId}.pdf"
  ├── originalFilename: string
  ├── summary: string
  ├── category: "EVENT" | "TASK" | "INFO" | "IGNORE"
  └── errorMessage: string | null

# 非正規化コレクション（日付範囲クエリの効率化）
users/{uid}/events/{eventId}
  ├── documentId: string    # 参照元文書
  ├── summary: string
  ├── start: string         # ISO8601
  ├── end: string           # ISO8601
  ├── location: string
  └── confidence: string    # HIGH | MEDIUM | LOW

users/{uid}/tasks/{taskId}
  ├── documentId: string    # 参照元文書
  ├── title: string
  ├── dueDate: string       # YYYY-MM-DD
  ├── assignee: string      # PARENT | CHILD
  ├── note: string
  └── completed: boolean
```

**冪等性の実装:** アップロード時に SHA-256 でコンテンツハッシュを計算し、同じハッシュの既存 DocumentRecord がある場合は解析をスキップして既存結果を返す。

### API 設計（主要エンドポイント）

```
# ドキュメント
POST /api/documents/upload    → 202 { id, status: "pending" }
GET  /api/documents           → 200 [DocumentRecord...]
GET  /api/documents/{id}      → 200 DocumentRecord with events/tasks
DELETE /api/documents/{id}    → 204

# イベント（全ドキュメントをまたいだビュー）
GET  /api/events?from=&to=&profileId=   → 200 [EventData...]

# タスク（全ドキュメントをまたいだビュー）
GET  /api/tasks?completed=false   → 200 [TaskData...]
PATCH /api/tasks/{id}             → 200 { completed: true }

# プロファイル管理
GET|POST /api/profiles
PUT|DELETE /api/profiles/{id}

# iCal フィード（認証不要、トークンベース）
GET /api/ical/{token}   → text/calendar

# ユーザー設定
GET|PATCH /api/settings   → { plan, documentsThisMonth, icalUrl, ... }
```

---

## 6. 既存コード再利用方針

### そのまま保持（変更なし）

| ファイル | 理由 |
|---|---|
| `v2/domain/models.py` (既存の dataclass) | `EventData`, `TaskData`, `DocumentAnalysis` は B2C でもそのまま使用 |
| `v2/adapters/google_*.py`, `todoist.py`, `slack.py` | レガシーバッチモード用に保持 |
| `v2/services/orchestrator.py` | バッチモード (Cloud Run Jobs) は引き続き個人用途で稼働 |
| `v2/entrypoints/cli.py`, `factory.py` | バッチモード用に保持 |
| `v2/logging_config.py` | Cloud Run 環境判定ロジックがそのまま使える |

### 変更（最小限）

| ファイル | 変更内容 |
|---|---|
| `v2/adapters/gemini.py:35-57` | `__init__` を変更: `vertexai.init()` をコンストラクタから除去し、外部から `GenerativeModel` インスタンスを受け取る形に。プロンプト・解析ロジック (行 148-304) は一切変更なし |
| `v2/domain/ports.py` | 5 つの新 ABC を追加 (`DocumentRepository`, `UserConfigRepository`, `BlobStorage`, `TaskQueue`, `CalendarFeedRenderer`) |
| `v2/domain/models.py` | 2 つの新 dataclass を追加 (`DocumentRecord`, `UserProfile`) |
| `v2/config.py` | B2C 用フィールドを追加 (`firebase_project_id`, `gcs_bucket`, `cloud_tasks_queue` 等) |

### 新規作成

| ファイル | 役割 |
|---|---|
| `v2/services/document_processor.py` | `orchestrator._process_single` を独立サービスに抽出 (バッチ/API 両方から利用) |
| `v2/adapters/firestore_repository.py` | Firestore CRUD (DocumentRepository, UserConfigRepository 実装) |
| `v2/adapters/cloud_storage.py` | GCS アップロード/ダウンロード (BlobStorage 実装) |
| `v2/adapters/cloud_tasks_queue.py` | Cloud Tasks キューイング (TaskQueue 実装) |
| `v2/adapters/ical_renderer.py` | iCal フィード生成 (CalendarFeedRenderer 実装) |
| `v2/adapters/email_notifier.py` | メール通知 (SendGrid) |
| `v2/adapters/webpush_notifier.py` | Web Push 通知 (pywebpush + VAPID) |
| `v2/entrypoints/api/` | FastAPI アプリケーション全体 |
| `v2/entrypoints/worker.py` | Cloud Tasks ワーカーエントリーポイント |
| `frontend/` | Next.js PWA フロントエンド全体 |
| `terraform/modules/cloud_run_service/` | Cloud Run Service モジュール |
| `terraform/modules/firestore/` | Firestore モジュール |
| `terraform/modules/firebase_hosting/` | Firebase Hosting モジュール |
| `terraform/modules/cloud_tasks/` | Cloud Tasks モジュール |

---

## 7. フロントエンド技術選定

**推奨スタック:** Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui

| 判断軸 | 選択 | 理由 |
|---|---|---|
| フレームワーク | Next.js 15 (App Router) | Firebase Hosting への静的エクスポート。PWA 対応 (`next-pwa`) |
| 認証 | Firebase Auth JS SDK | サーバー不要で直接統合 |
| カメラ | `navigator.mediaDevices` | ライブラリ不要のネイティブ API |
| カレンダー UI | react-big-calendar | 月/週ビューの実績あるライブラリ |
| PWA | next-pwa (Workbox) | Service Worker 自動生成 |

---

## 8. フェーズ分け

### Phase 0: 基盤準備（推定 1 週間）
**ゴール:** 既存コードを壊さずに B2C の土台を作る

- `_process_single` を `DocumentProcessor` として独立サービスに抽出
- `GeminiDocumentAnalyzer.__init__` から `vertexai.init()` を除去
- `domain/ports.py` に 5 ポート追加、`domain/models.py` に 2 モデル追加
- `pyproject.toml` の依存関係整理（追加: fastapi/firebase-admin/firestore 等、削除: pandas/functions-framework）
- 確認: `pytest tests/unit/ tests/integration/` が全て通る

### Phase 1: バックエンド API（推定 2 週間）
**ゴール:** `curl` で PDF をアップロードし、解析結果を取得できる

- Firestore / Cloud Storage / Cloud Tasks アダプター実装
- FastAPI アプリケーション + Firebase Auth ミドルウェア
- Cloud Tasks ワーカー実装
- Terraform: Cloud Run Service / Firestore / Cloud Storage / Cloud Tasks モジュール追加
- 確認: `curl -X POST .../upload -F file=@test.pdf` → 202、数十秒後に `GET .../events` で結果取得

### Phase 2: PWA フロントエンド（推定 2 週間）
**ゴール:** ブラウザでサインアップ → アップロード → 結果確認が完結する

- Next.js 15 プロジェクト初期化
- Firebase Auth 統合（Google サインイン + Email/Password）
- カメラ撮影 + ドラッグ&ドロップ UI
- ダッシュボード（カレンダービュー + タスク一覧）
- プロファイル管理設定画面
- PWA manifest + Service Worker
- Firebase Hosting デプロイ

### Phase 3: 通知 & iCal（推定 1 週間）
**ゴール:** 受動的にも情報が届く仕組み

- iCal フィード生成エンドポイント
- Email 通知アダプター（SendGrid）
- Web Push 通知アダプター（pywebpush + VAPID）
- 朝のダイジェストメール（Cloud Scheduler）

### Phase 4: 品質 & ローンチ準備（推定 1 週間）
**ゴール:** 本番リリース可能な状態

- 冪等性の完全実装（content hash による重複排除）
- 無料プランのレート制限（月5枚チェック）
- Gemini API リトライ（tenacity）
- 構造化 JSON ログ + Cloud Monitoring アラート（エラー率・レイテンシ・Vertex AI クォータ）
- プライバシーポリシー・利用規約ページ

---

## 9. コスト見積もり

| サービス | 無料枠 | MVP 想定使用量 | 月額コスト |
|---|---|---|---|
| Cloud Run Service | 2M リクエスト、360k vCPU-sec/月 | ~10K リクエスト | **¥0** |
| Cloud Tasks | 1M オペレーション/月 | ~1K | **¥0** |
| Firestore | 50K reads/日、20K writes/日、1GB | <5K 文書 | **¥0** |
| Cloud Storage | 5GB | ~1GB | **¥0** |
| Firebase Auth | 10K MAU 無料 | <1K ユーザー | **¥0** |
| Firebase Hosting | 10GB 無料 | <1GB | **¥0** |
| SendGrid | 100通/日 無料 | <100通/日 | **¥0** |
| **Vertex AI (Gemini 2.5 Pro)** | なし（従量課金） | ~1,000 解析/月 | **$20~50** |
| **合計** | | | **$20~50/月** |

**結論:** ランニングコストはほぼ Gemini API 料金のみ。1 文書あたり ¥3~10 のコストで、¥300/月のプレミアムプランでは月 20 枚以上使うヘビーユーザーで黒字になる。

---

## 10. 課金モデル詳細

```
無料プラン: 月5枚まで解析
  → 最大コスト: ¥50/月/ユーザー (許容範囲)
  → 目的: 「便利だけどもっと使いたい」の体験を作る

プレミアムプラン: ¥300/月 (無制限 + 家族共有)
  → 月20枚使うヘビーユーザーでもコスト ¥200 → 粗利 ¥100+
  → 家族共有機能をプレミアム限定にすると付加価値が上がる
```

**将来の課金拡張:** 学期課金 (¥800~1,200/学期)、年額割引 (¥2,800/年) も学校のサイクルに合わせて有効。

---

## 11. リスクと対策

| リスク | 深刻度 | 対策 |
|---|---|---|
| **解析精度の低下** | 高 | 手書きプリント、斜め撮影、逆光で精度低下 → MVP 段階で「精度フィードバック」機能を付けて改善ループを回す |
| **ユーザー獲得が難しい** | 高 | 保護者コミュニティ (PTA, ママ友 SNS) への口コミ戦略。「子どもの学校で使っている人が多い」というネットワーク効果を狙う |
| **TimeTree による先行** | 中 | タスク・持ち物の抽出精度と学校特化の深さで差別化。B2B 展開も視野に入れた展開 |
| **学校の DX 化で市場縮小** | 中 | スクリレ/テトルが普及しても「カレンダー連携しない」ギャップは当面残る |
| **季節変動** | 中 | 夏休み・冬休みは配布物激減 → 年額プランや学期課金で吸収 |
| **Gemini API コスト超過** | 低 | 無料枠の月5枚制限と有料プランの料金設計で吸収。大量スパムアップロードには reCAPTCHA / レート制限 |

---

## 12. 将来の B2B ピボット

### 設計上の準備

このアーキテクチャは、最初から B2B ピボットの余地を残して設計されている。

**ポイント:** ビジネスロジック (`DocumentProcessor`, `GeminiDocumentAnalyzer`) は完全にテナント非依存。テナントスコーピングは Adapter 層と API 層のみで管理。

### B2B ピボット時に必要な追加開発

| 機能 | 変更スコープ | 概算工数 |
|---|---|---|
| 組織 (学校・PTA) エンティティ | Firestore に `organizations/{orgId}` 追加、新ドメインモデル | 1~2 週間 |
| ロールベースアクセス制御 (admin/teacher/parent) | Firebase Auth カスタムクレーム | 1 週間 |
| 管理者ダッシュボード | 新規フロントエンドページ + API エンドポイント | 2~3 週間 |
| 組織単位の課金 | Stripe 統合アダプター | 2~3 週間 |
| クラス共有カレンダー | events のスコープを user → organization に拡張 | 1 週間 |
| SSO (SAML/OIDC) | Firebase Auth カスタムプロバイダー | 2 週間 |

### Firestore の将来の拡張パス

```
# 現在 (B2C)
users/{uid}/...

# B2B ピボット後
organizations/{orgId}/
  ├── classes/{classId}/...
  └── documents/{documentId}/...

users/{uid}/
  ├── orgId: string (所属組織)
  └── role: "admin" | "teacher" | "parent"
```

---

## 参考: 関連する既存ファイル

- 現状分析: `docs/review/nonfunctional-analysis-2026-02-23.md`
- コア解析ロジック: `v2/adapters/gemini.py`
- ドメインモデル: `v2/domain/models.py`
- ポート定義: `v2/domain/ports.py`
- 1ファイル処理の抽出元: `v2/services/orchestrator.py:106-151`
