"""DocumentProcessor - 単一ファイルのAI解析サービス

設計方針:
- ストレージ操作（GCS）はここでは行わない
- 「content → DocumentAnalysis」の変換のみに責務を絞る
"""

from __future__ import annotations

import logging

from v2.domain.models import DocumentAnalysis, UserProfile
from v2.domain.ports import DocumentAnalyzer

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    単一ファイルのAI解析処理。

    DocumentAnalyzer を受け取り、ファイル内容から DocumentAnalysis を生成する。
    ログ記録と例外の再送出を行う薄いラッパーとして、
    バッチ・API ワーカーの両方から共通利用できる。
    """

    def __init__(self, analyzer: DocumentAnalyzer) -> None:
        """
        Args:
            analyzer: 文書解析器（GeminiDocumentAnalyzer 等）
        """
        self._analyzer = analyzer

    def process(
        self,
        content: bytes,
        mime_type: str,
        profiles: dict[str, UserProfile],
        rules: list | None = None,
    ) -> DocumentAnalysis:
        """
        ファイル内容を解析して DocumentAnalysis を返す。

        Args:
            content: ファイルのバイナリ内容
            mime_type: MIMEタイプ（例: "application/pdf", "image/jpeg"）
            profiles: プロファイル辞書 (profile_id -> UserProfile)
            rules: 適用するルールのリスト（省略可）

        Returns:
            DocumentAnalysis: 解析結果（category/events/tasks/summary 等）

        Raises:
            Exception: 解析に失敗した場合（ログ記録後に再送出）
        """
        logger.info(
            "Processing document: mime_type=%s, size=%d bytes, profiles=%d",
            mime_type,
            len(content),
            len(profiles),
        )

        try:
            analysis = self._analyzer.analyze(content, mime_type, profiles, rules)
            logger.info(
                "Processing complete: category=%s, events=%d, tasks=%d",
                analysis.category.value,
                len(analysis.events),
                len(analysis.tasks),
            )
            return analysis
        except Exception:
            logger.exception("Document processing failed: mime_type=%s", mime_type)
            raise
