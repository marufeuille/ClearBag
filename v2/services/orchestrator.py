"""Orchestrator - メインワークフロー

既存 src/core.py の責務を再設計。
Ports（Protocol）にのみ依存し、外部APIの実装詳細からは独立。
"""

from __future__ import annotations
import logging
from datetime import datetime
from v2.domain.ports import (
    ConfigSource,
    FileStorage,
    DocumentAnalyzer,
)
from v2.domain.models import FileInfo, ProcessingResult
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
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("🚀 School Agent v2 Started")
        logger.info("⏰ Start time: %s", start_time.isoformat())
        logger.info("=" * 80)

        # 1. 設定読み込み
        logger.info("📚 [Step 1/3] Loading configuration...")
        try:
            config_start = datetime.now()
            profiles = self._config.load_profiles()
            rules = self._config.load_rules()
            config_duration = (datetime.now() - config_start).total_seconds()
            logger.info("✅ [Step 1/3] Loaded %d profiles and %d rules in %.2f seconds",
                       len(profiles), len(rules), config_duration)
        except Exception as e:
            logger.exception("❌ [Step 1/3] Failed to load config: %s", e)
            return []

        # 2. Inboxスキャン
        logger.info("📂 [Step 2/3] Scanning Inbox...")
        scan_start = datetime.now()
        files = self._storage.list_inbox_files()
        scan_duration = (datetime.now() - scan_start).total_seconds()

        if not files:
            logger.warning("⚠️ [Step 2/3] No files found in Inbox (scan took %.2f seconds)", scan_duration)
            logger.warning("⚠️ Possible reasons:")
            logger.warning("  1. Inbox is genuinely empty")
            logger.warning("  2. Files were uploaded but not yet visible to the service account")
            logger.warning("  3. Permission issues with the Inbox folder")
            logger.warning("  4. Drive API caching/propagation delay")
            return []

        logger.info("✅ [Step 2/3] Found %d files to process (scan took %.2f seconds)",
                   len(files), scan_duration)

        # 3. 各ファイルを処理
        logger.info("🔄 [Step 3/3] Processing files...")
        processing_start = datetime.now()
        results: list[ProcessingResult] = []
        for idx, file_info in enumerate(files, 1):
            logger.info("📄 [%d/%d] Processing: %s", idx, len(files), file_info.name)
            result = self._process_single(file_info, profiles, rules)
            results.append(result)

        processing_duration = (datetime.now() - processing_start).total_seconds()
        total_duration = (datetime.now() - start_time).total_seconds()

        logger.info("=" * 80)
        logger.info("✅ Processing complete")
        logger.info("⏱️ Total time: %.2f seconds", total_duration)
        logger.info("📊 Files processed: %d (%.2f sec)", len(results), processing_duration)
        logger.info("📊 Successful: %d", len([r for r in results if not r.error]))
        logger.info("📊 Failed: %d", len([r for r in results if r.error]))
        logger.info("⏰ End time: %s", datetime.now().isoformat())
        logger.info("=" * 80)

        return results

    def _process_single(
        self, file_info: FileInfo, profiles, rules
    ) -> ProcessingResult:
        """
        1ファイルの処理。エラーが発生しても他のファイル処理は続行。

        Args:
            file_info: ファイル情報
            profiles: Profile ID -> Profile の辞書
            rules: ルールのリスト

        Returns:
            ProcessingResult: 処理結果（エラー情報含む）
        """
        file_start = datetime.now()
        logger.info("-" * 80)
        logger.info("📄 Processing file: %s", file_info.name)
        logger.info("📄 File ID: %s", file_info.id)
        logger.info("📄 MIME type: %s", file_info.mime_type)
        logger.info("-" * 80)

        try:
            # ダウンロード
            download_start = datetime.now()
            content = self._storage.download(file_info.id)
            download_duration = (datetime.now() - download_start).total_seconds()
            logger.info("⬇️ Downloaded %d bytes in %.2f seconds", len(content), download_duration)

            # Geminiで解析
            logger.info("🤖 Analyzing with Gemini...")
            analysis_start = datetime.now()
            analysis = self._analyzer.analyze(
                content, file_info.mime_type, profiles, rules
            )
            analysis_duration = (datetime.now() - analysis_start).total_seconds()
            logger.info("✅ Analysis complete in %.2f seconds: %s", analysis_duration, analysis.summary)

            # アクション実行
            logger.info("⚡ Dispatching actions...")
            dispatch_start = datetime.now()
            dispatch_result = self._dispatcher.dispatch(
                file_info, analysis, profiles
            )
            dispatch_duration = (datetime.now() - dispatch_start).total_seconds()
            logger.info("✅ Actions dispatched in %.2f seconds", dispatch_duration)

            # アーカイブ
            archive_name = analysis.archive_filename or f"PROCESSED_{file_info.name}"
            logger.info("📦 Archiving as: %s", archive_name)
            archive_start = datetime.now()
            self._storage.archive(file_info.id, archive_name)
            archive_duration = (datetime.now() - archive_start).total_seconds()
            logger.info("✅ Archived in %.2f seconds", archive_duration)

            file_total_duration = (datetime.now() - file_start).total_seconds()
            logger.info("✅ File processing completed in %.2f seconds", file_total_duration)

            return ProcessingResult(
                file_info=file_info,
                analysis=analysis,
                events_created=dispatch_result.events_created,
                tasks_created=dispatch_result.tasks_created,
                notification_sent=dispatch_result.notification_sent,
                archived=True,
            )

        except Exception as e:
            file_error_duration = (datetime.now() - file_start).total_seconds()
            logger.exception("❌ Error processing %s after %.2f seconds: %s",
                           file_info.name, file_error_duration, e)
            return ProcessingResult(file_info=file_info, error=str(e))
