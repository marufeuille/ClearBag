"""Orchestrator - メインワークフロー

既存 src/core.py の責務を再設計。
Ports（Protocol）にのみ依存し、外部APIの実装詳細からは独立。
"""

from __future__ import annotations

import logging

from v2.domain.models import FileInfo, ProcessingResult
from v2.domain.ports import (
    ConfigSource,
    DocumentAnalyzer,
    FileStorage,
)
from v2.services.action_dispatcher import ActionDispatcher

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    学校配布物処理の全体ワークフローを統合する。

    処理フロー:
    1. Google Sheetsから設定読み込み
    2. Inboxフォルダのファイル一覧取得
    3. 各ファイルについて:
       - ダウンロード
       - Geminiで解析
       - アクション実行（Calendar/Todoist/Slack）
       - アーカイブ
    """

    def __init__(
        self,
        config_source: ConfigSource,
        file_storage: FileStorage,
        analyzer: DocumentAnalyzer,
        action_dispatcher: ActionDispatcher,
    ) -> None:
        """
        Args:
            config_source: 設定読み込み（Google Sheets等）
            file_storage: ファイル操作（Google Drive等）
            analyzer: 文書解析（Gemini等）
            action_dispatcher: アクション振り分け
        """
        self._config = config_source
        self._storage = file_storage
        self._analyzer = analyzer
        self._dispatcher = action_dispatcher

    def run(self) -> list[ProcessingResult]:
        """
        Inboxの全ファイルを処理する。

        Returns:
            list[ProcessingResult]: 各ファイルの処理結果
        """
        logger.info("=== School Agent v2 Started ===")

        # 1. 設定読み込み
        logger.info("Loading configuration...")
        try:
            profiles = self._config.load_profiles()
            rules = self._config.load_rules()
            logger.info("Loaded %d profiles and %d rules", len(profiles), len(rules))
        except Exception as e:
            logger.exception("Failed to load config: %s", e)
            return []

        # 2. Inboxスキャン
        logger.info("Scanning Inbox...")
        files = self._storage.list_inbox_files()
        if not files:
            logger.info("No files found in Inbox.")
            return []

        logger.info("Found %d files to process", len(files))

        # 3. 各ファイルを処理
        results: list[ProcessingResult] = []
        for file_info in files:
            result = self._process_single(file_info, profiles, rules)
            results.append(result)

        logger.info("=== Processing complete: %d files processed ===", len(results))
        return results

    def _process_single(self, file_info: FileInfo, profiles, rules) -> ProcessingResult:
        """
        1ファイルの処理。エラーが発生しても他のファイル処理は続行。

        Args:
            file_info: ファイル情報
            profiles: Profile ID -> Profile の辞書
            rules: ルールのリスト

        Returns:
            ProcessingResult: 処理結果（エラー情報含む）
        """
        logger.info("--- Processing: %s ---", file_info.name)

        try:
            # ダウンロード
            content = self._storage.download(file_info.id)
            logger.debug("Downloaded %d bytes", len(content))

            # Geminiで解析
            logger.info("Analyzing with Gemini...")
            analysis = self._analyzer.analyze(
                content, file_info.mime_type, profiles, rules
            )
            logger.info("Analysis complete: %s", analysis.summary)

            # アクション実行
            dispatch_result = self._dispatcher.dispatch(file_info, analysis, profiles)

            # アーカイブ
            archive_name = analysis.archive_filename or f"PROCESSED_{file_info.name}"
            logger.info("Archiving as: %s", archive_name)
            self._storage.archive(file_info.id, archive_name)

            return ProcessingResult(
                file_info=file_info,
                analysis=analysis,
                events_created=dispatch_result.events_created,
                tasks_created=dispatch_result.tasks_created,
                notification_sent=dispatch_result.notification_sent,
                archived=True,
            )

        except Exception as e:
            logger.exception("Error processing %s: %s", file_info.name, e)
            return ProcessingResult(file_info=file_info, error=str(e))
