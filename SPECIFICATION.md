# School Agent 仕様書

## 1. 目的
学校や保育園から配布される非構造化データ（プリント類）の処理を自動化し、親の手を介さずにカレンダー登録やタスク化を行うこと。
単なるOCRツールではなく、**「内容を理解し、親の代わりに整理してくれる秘書」** として機能する。

## 2. 要件

### 2.1 機能要件
1.  **入力:** 特定のGoogle Driveフォルダ (`Inbox`) にある画像やPDFを検知・読み込み。
2.  **理解・抽出:** LLM (Gemini) を使用して、文書から「イベント」「アクション（タスク）」「メタデータ」を抽出。
3.  **設定:** 対象となる人物（子供・親）やルールを外部ソース（Google Sheets）から動的に読み込む。
4.  **スケジュール登録:** 抽出したイベントを対象者のGoogleカレンダーに登録。
5.  **タスク管理:** アクションをTodoistに登録し、Slackで通知。
6.  **整理:** 処理済みファイルを検索可能な形式 (`YYYYMMDD_タイトル`) にリネームし、`Archive` フォルダへ移動。

### 2.2 非機能要件
*   **Google Ecosystem:** 主にGoogle Cloud (Drive, Vertex AI, Calendar) 上で構築。
*   **拡張性:** 子供の人数や学年の変化にコード修正なしで対応可能（Config駆動）。
*   **シンプルさ:** Pythonスクリプトのループとして実装。

---

## 3. システムアーキテクチャ

```mermaid
graph TD
    subgraph Storage
    Inbox[Google Drive (Inbox)]
    Archive[Google Drive (Archive)]
    Config[Google Sheets (Config)]
    end

    subgraph Compute
    Agent[Python Script (Agent Loop)]
    end

    subgraph AI
    LLM[Gemini 1.5 Pro]
    end

    subgraph UserInterface
    Cal[Google Calendar]
    Slack[Slack Notification]
    Todoist[Todoist Task]
    end

    Inbox -->|1. 新規ファイルスキャン| Agent
    Config -->|2. ルール/プロファイル読込| Agent
    Agent <-->|3. 解析 & 関数呼び出し| LLM
    Agent -->|4. イベント作成| Cal
    Agent -->|5. 通知| Slack
    Agent -->|6. タスク作成| Todoist
    Agent -->|7. リネーム & 移動| Archive
```

---

## 4. データモデル (設定)

設定は **Google Sheets** で管理します。

### シート1: `Profiles`
家族メンバーや処理対象を定義します。

| ID | Name | Grade | Keywords | Calendar_ID |
| :--- | :--- | :--- | :--- | :--- |
| `CHILD1` | 子供の名前 | 小3 | キーワード... | `calendar_id_1...` |
| `CHILD2` | 子供の名前 | 小1 | キーワード... | `calendar_id_2...` |
| `PARENTS`| 両親 | - | PTAなど | `primary` |

### シート2: `Rules`
特定の解析ルールやアクションルールを定義します。

| Rule_ID | Target_Profile | Rule_Type | Content |
| :--- | :--- | :--- | :--- |
| `R001` | `CHILD1` | `REMINDER` | 持ち物が必要なイベントは3日前にタスク期限を設定する。 |
| `R002` | `ALL` | `IGNORE` | 広告や重要でないチラシは無視する。 |
| `R003` | `ALL` | `NAMING` | ファイル名は `YYYYMMDD_タイトル` にリネームする。 |

---

## 5. インターフェース設計 (LLM)

### 5.1 システムプロンプト
> あなたは家族の事務を管理する優秀なAIエージェントです。
> 提供された画像/PDFを読み、Google Sheetsから読み込まれた `Profiles` と `Rules` に基づいて、
> 適切なツール（カレンダー、タスク、アーカイブ）を実行するための情報を抽出してください。

### 5.2 出力スキーマ (JSON)

```json
{
  "summary": "文書の要約。",
  "category": "EVENT", 
  "related_profile_ids": ["CHILD1"],
  "events": [
    {
      "summary": "[長男] 遠足",
      "start": "2025-10-25T08:30:00",
      "end": "2025-10-25T15:00:00",
      "location": "場所名",
      "description": "詳細..."
    }
  ],
  "tasks": [
    {
      "title": "同意書の提出",
      "due_date": "2025-10-10",
      "assignee": "PARENT",
      "note": "署名が必要です。"
    }
  ],
  "archive_filename": "20251025_遠足_長男.pdf"
}
```

---

## 6. 処理フロー

1.  **初期化:** Google Sheetsから `Profiles` と `Rules` を読み込む。
2.  **スキャン:** `Inbox` 内のファイルリストを取得。
3.  **ループ:** 各ファイルについて:
    *   **思考 (Think):** コンテキストと共にGeminiにアップロード。
    *   **行動 (Act):**
        *   `add_calendar_event` (カレンダー登録)
        *   `create_todoist_task` (タスク登録)
        *   `send_slack_notification` (通知)
    *   **完了 (Finish):** ファイルをリネームして `Archive` へ移動。