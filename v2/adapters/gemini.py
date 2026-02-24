"""Gemini Document Analyzer Adapter

DocumentAnalyzer ABCの実装。
既存 src/gemini_client.py を移植し、ABCに準拠。

vertexai.init() はコンストラクタから分離されており、
呼び出し側（factory等）が事前に初期化した GenerativeModel を渡す。
"""

import json
import logging

import vertexai.preview.generative_models as generative_models
from vertexai.generative_models import GenerativeModel, Part

from v2.domain.models import (
    Category,
    DocumentAnalysis,
    EventData,
    Profile,
    Rule,
    TaskData,
)
from v2.domain.ports import DocumentAnalyzer

logger = logging.getLogger(__name__)


class GeminiDocumentAnalyzer(DocumentAnalyzer):
    """
    Gemini 2.5 Proを使った文書解析実装。

    PDF/画像から構造化データ（イベント・タスク・要約）を抽出する。

    vertexai.init() は外部で実行済みであることを前提とし、
    初期化済みの GenerativeModel インスタンスを受け取る。
    これにより、テスト時のモック差し替えとマルチテナント化が容易になる。
    """

    def __init__(self, model: GenerativeModel) -> None:
        """
        Args:
            model: 初期化済みの GenerativeModel インスタンス。
                   呼び出し側で vertexai.init() を実行してから渡すこと。
        """
        if model is None:
            raise ValueError("model is required")

        self._model = model

        logger.info("GeminiDocumentAnalyzer initialized")

    def analyze(
        self,
        content: bytes,
        mime_type: str,
        profiles: dict[str, Profile],
        rules: list[Rule],
    ) -> DocumentAnalysis:
        """
        文書を解析して構造化データを抽出。

        Args:
            content: ファイルの内容（バイナリ）
            mime_type: MIMEタイプ（例: application/pdf, image/jpeg）
            profiles: プロファイル辞書
            rules: ルールリスト

        Returns:
            DocumentAnalysis: 解析結果

        Raises:
            Exception: 解析に失敗した場合
        """
        try:
            # プロンプト構築
            self._build_system_prompt()
            user_prompt = self._build_user_prompt(profiles, rules)

            # Gemini API呼び出し
            document_part = Part.from_data(data=content, mime_type=mime_type)

            generation_config = {
                "max_output_tokens": 8192,
                "temperature": 0.2,
                "top_p": 0.95,
                "response_mime_type": "application/json",
            }

            HarmCategory = generative_models.HarmCategory
            HarmBlock = generative_models.HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlock.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlock.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlock.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlock.BLOCK_MEDIUM_AND_ABOVE,
            }

            responses = self._model.generate_content(
                [document_part, user_prompt],
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=False,
            )

            # トークン使用量をログに記録
            usage = getattr(responses, "usage_metadata", None)
            if usage:
                logger.info(
                    "Gemini token usage: input=%d, output=%d, total=%d",
                    usage.prompt_token_count,
                    usage.candidates_token_count,
                    usage.total_token_count,
                )

            # JSONレスポンスをパース
            raw_json = self._parse_response(responses.text)
            analysis = self._convert_to_domain_model(raw_json)

            logger.info(
                "Document analysis complete: category=%s, events=%d, tasks=%d",
                analysis.category,
                len(analysis.events),
                len(analysis.tasks),
            )

            return analysis

        except Exception:
            logger.exception("Failed to analyze document")
            raise

    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """
あなたは家庭の事務を司る優秀なAIエージェントです。
提供される画像/PDFの内容を読み取り、提供された `Profiles` と `Rules` に基づいて、
適切なツール（カレンダー登録、タスク作成、アーカイブ）を選択・実行するための情報を抽出してください。

出力は必ずJSON形式で行ってください。Markdownのコードブロックは不要です。
"""

    def _build_user_prompt(
        self, profiles: dict[str, Profile], rules: list[Rule]
    ) -> str:
        """ユーザープロンプトを構築"""
        # ProfilesをJSONに変換（dataclass → dict）
        profiles_dict = {
            pid: {
                "id": p.id,
                "name": p.name,
                "grade": p.grade,
                "keywords": p.keywords,
                "calendar_id": p.calendar_id,
            }
            for pid, p in profiles.items()
        }

        # RulesをJSONに変換（dataclass → dict）
        rules_list = [
            {
                "rule_id": r.rule_id,
                "target_profile": r.target_profile,
                "rule_type": r.rule_type,
                "content": r.content,
            }
            for r in rules
        ]

        profiles_str = json.dumps(profiles_dict, ensure_ascii=False, indent=2)
        rules_str = json.dumps(rules_list, ensure_ascii=False, indent=2)

        return f"""
## Context Data

### Profiles (対象者定義)
{profiles_str}

### Rules (判断ルール)
{rules_str}

## Output Schema

以下のJSON構造で出力してください:
{{
  "summary": "文書の要約",
  "category": "EVENT" | "TASK" | "INFO" | "IGNORE",
  "related_profile_ids": ["関連するProfileIDのリスト"],
  "events": [
    {{
      "summary": "カレンダー登録用タイトル (例: [長男] 遠足)",
      "start": "YYYY-MM-DDTHH:MM:SS (ISO8601)",
      "end": "YYYY-MM-DDTHH:MM:SS (ISO8601)",
      "location": "場所",
      "description": "詳細説明",
      "confidence": "HIGH" | "MEDIUM" | "LOW"
    }}
  ],
  "tasks": [
    {{
      "title": "タスク名",
      "due_date": "YYYY-MM-DD",
      "assignee": "PARENT" | "CHILD",
      "note": "メモ"
    }}
  ],
  "archive_filename": "リネーム後のファイル名 (例: YYYYMMDD_タイトル_対象.pdf)"
}}

## Instructions

1. 文書の日付、イベントの日時を正確に読み取ってください。年は文書内の情報や現在の日付から推測してください。
2. Rulesにあるルールを適用して、タスクの期限や無視するかどうかを判断してください。
3. ファイル名は `YYYYMMDD_タイトル` の形式にしてください。
"""

    def _parse_response(self, response_text: str) -> dict:
        """
        Geminiのレスポンスをパース。

        Markdownコードブロックを除去してJSONとして解釈する。
        """
        text = response_text.strip()

        # Markdownコードブロックの除去
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s", e)
            logger.error("Raw response: %s", response_text)
            raise

    def _convert_to_domain_model(self, raw_json: dict) -> DocumentAnalysis:
        """
        生のJSON辞書をドメインモデル（DocumentAnalysis）に変換。

        Args:
            raw_json: Geminiからの生JSON

        Returns:
            DocumentAnalysis: ドメインモデル
        """
        # Category変換
        category_str = raw_json.get("category", "INFO")
        try:
            category = Category(category_str)
        except ValueError:
            logger.warning("Invalid category: %s, using INFO", category_str)
            category = Category.INFO

        # Events変換
        events = [
            EventData(
                summary=e.get("summary", ""),
                start=e.get("start", ""),
                end=e.get("end", ""),
                location=e.get("location", ""),
                description=e.get("description", ""),
                confidence=e.get("confidence", "HIGH"),
            )
            for e in raw_json.get("events", [])
        ]

        # Tasks変換
        tasks = [
            TaskData(
                title=t.get("title", ""),
                due_date=t.get("due_date", ""),
                assignee=t.get("assignee", "PARENT"),
                note=t.get("note", ""),
            )
            for t in raw_json.get("tasks", [])
        ]

        return DocumentAnalysis(
            summary=raw_json.get("summary", ""),
            category=category,
            related_profile_ids=raw_json.get("related_profile_ids", []),
            events=events,
            tasks=tasks,
            archive_filename=raw_json.get("archive_filename", ""),
        )
