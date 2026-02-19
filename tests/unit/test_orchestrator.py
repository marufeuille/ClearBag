"""Orchestrator のテスト"""

from unittest.mock import MagicMock

import pytest

from v2.domain.models import Category, DocumentAnalysis, FileInfo, ProcessingResult
from v2.services.action_dispatcher import DispatchResult
from v2.services.orchestrator import Orchestrator


class TestOrchestrator:
    """Orchestrator の単体テスト"""

    def test_run_processes_single_file_successfully(
        self,
        mock_config,
        mock_storage,
        mock_analyzer,
        mock_calendar,
        mock_task_service,
        mock_notifier,
        sample_file_info,
        sample_analysis,
    ):
        """1ファイルの正常処理フロー"""
        # Arrange
        from v2.services.action_dispatcher import ActionDispatcher

        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)
        orchestrator = Orchestrator(mock_config, mock_storage, mock_analyzer, dispatcher)

        # Act
        results = orchestrator.run()

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.archived is True
        assert result.error is None
        assert result.file_info == sample_file_info
        assert result.analysis == sample_analysis
        assert result.notification_sent is True

        # 各サービスが呼ばれたことを確認
        mock_config.load_profiles.assert_called_once()
        mock_config.load_rules.assert_called_once()
        mock_storage.list_inbox_files.assert_called_once()
        mock_storage.download.assert_called_once_with(sample_file_info.id)
        mock_analyzer.analyze.assert_called_once()
        mock_storage.archive.assert_called_once_with(
            sample_file_info.id, sample_analysis.archive_filename
        )

    def test_run_with_empty_inbox(
        self,
        mock_config,
        mock_storage,
        mock_analyzer,
        mock_calendar,
        mock_task_service,
        mock_notifier,
    ):
        """Inboxが空の場合は空リストを返す"""
        # Arrange
        from v2.services.action_dispatcher import ActionDispatcher

        mock_storage.list_inbox_files.return_value = []
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)
        orchestrator = Orchestrator(mock_config, mock_storage, mock_analyzer, dispatcher)

        # Act
        results = orchestrator.run()

        # Assert
        assert results == []
        mock_storage.download.assert_not_called()
        mock_analyzer.analyze.assert_not_called()

    def test_run_handles_config_load_error(
        self,
        mock_config,
        mock_storage,
        mock_analyzer,
        mock_calendar,
        mock_task_service,
        mock_notifier,
    ):
        """設定読み込み失敗時は空リストを返す"""
        # Arrange
        from v2.services.action_dispatcher import ActionDispatcher

        mock_config.load_profiles.side_effect = Exception("Config error")
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)
        orchestrator = Orchestrator(mock_config, mock_storage, mock_analyzer, dispatcher)

        # Act
        results = orchestrator.run()

        # Assert
        assert results == []
        mock_storage.list_inbox_files.assert_not_called()

    def test_run_handles_download_error(
        self,
        mock_config,
        mock_storage,
        mock_analyzer,
        mock_calendar,
        mock_task_service,
        mock_notifier,
        sample_file_info,
    ):
        """ファイルダウンロード失敗時はエラー情報を含むResultを返す"""
        # Arrange
        from v2.services.action_dispatcher import ActionDispatcher

        mock_storage.download.side_effect = Exception("Download failed")
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)
        orchestrator = Orchestrator(mock_config, mock_storage, mock_analyzer, dispatcher)

        # Act
        results = orchestrator.run()

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.error is not None
        assert "Download failed" in result.error
        assert result.archived is False
        assert result.analysis is None

    def test_run_handles_analysis_error(
        self,
        mock_config,
        mock_storage,
        mock_analyzer,
        mock_calendar,
        mock_task_service,
        mock_notifier,
        sample_file_info,
    ):
        """解析失敗時はエラー情報を含むResultを返す"""
        # Arrange
        from v2.services.action_dispatcher import ActionDispatcher

        mock_analyzer.analyze.side_effect = Exception("Analysis failed")
        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)
        orchestrator = Orchestrator(mock_config, mock_storage, mock_analyzer, dispatcher)

        # Act
        results = orchestrator.run()

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.error is not None
        assert "Analysis failed" in result.error
        assert result.archived is False

    def test_run_processes_multiple_files(
        self,
        mock_config,
        mock_storage,
        mock_analyzer,
        mock_calendar,
        mock_task_service,
        mock_notifier,
    ):
        """複数ファイルが順次処理される"""
        # Arrange
        from v2.services.action_dispatcher import ActionDispatcher

        file1 = FileInfo(id="f1", name="file1.pdf", mime_type="application/pdf")
        file2 = FileInfo(id="f2", name="file2.pdf", mime_type="application/pdf")
        mock_storage.list_inbox_files.return_value = [file1, file2]

        analysis1 = DocumentAnalysis(
            summary="文書1",
            category=Category.EVENT,
            archive_filename="20260425_file1.pdf",
        )
        analysis2 = DocumentAnalysis(
            summary="文書2",
            category=Category.TASK,
            archive_filename="20260426_file2.pdf",
        )
        mock_analyzer.analyze.side_effect = [analysis1, analysis2]

        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)
        orchestrator = Orchestrator(mock_config, mock_storage, mock_analyzer, dispatcher)

        # Act
        results = orchestrator.run()

        # Assert
        assert len(results) == 2
        assert results[0].file_info == file1
        assert results[1].file_info == file2
        assert results[0].analysis == analysis1
        assert results[1].analysis == analysis2
        assert mock_storage.download.call_count == 2
        assert mock_analyzer.analyze.call_count == 2
        assert mock_storage.archive.call_count == 2

    def test_run_continues_after_single_file_error(
        self,
        mock_config,
        mock_storage,
        mock_analyzer,
        mock_calendar,
        mock_task_service,
        mock_notifier,
    ):
        """1ファイルのエラー後も他のファイル処理は続行される"""
        # Arrange
        from v2.services.action_dispatcher import ActionDispatcher

        file1 = FileInfo(id="f1", name="file1.pdf", mime_type="application/pdf")
        file2 = FileInfo(id="f2", name="file2.pdf", mime_type="application/pdf")
        mock_storage.list_inbox_files.return_value = [file1, file2]

        # file1はダウンロードエラー、file2は成功
        mock_storage.download.side_effect = [
            Exception("Download failed"),
            b"file2-content",
        ]
        mock_analyzer.analyze.return_value = DocumentAnalysis(
            summary="文書2",
            category=Category.INFO,
            archive_filename="file2.pdf",
        )

        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)
        orchestrator = Orchestrator(mock_config, mock_storage, mock_analyzer, dispatcher)

        # Act
        results = orchestrator.run()

        # Assert
        assert len(results) == 2
        assert results[0].error is not None  # file1はエラー
        assert results[1].error is None  # file2は成功
        assert results[1].archived is True

    def test_archive_uses_fallback_name_when_gemini_returns_empty(
        self,
        mock_config,
        mock_storage,
        mock_analyzer,
        mock_calendar,
        mock_task_service,
        mock_notifier,
        sample_file_info,
    ):
        """Geminiがarchive_filenameを返さない場合はフォールバック名を使う"""
        # Arrange
        from v2.services.action_dispatcher import ActionDispatcher

        analysis_no_filename = DocumentAnalysis(
            summary="テスト", category=Category.INFO, archive_filename=""
        )
        mock_analyzer.analyze.return_value = analysis_no_filename

        dispatcher = ActionDispatcher(mock_calendar, mock_task_service, mock_notifier)
        orchestrator = Orchestrator(mock_config, mock_storage, mock_analyzer, dispatcher)

        # Act
        orchestrator.run()

        # Assert
        expected_name = f"PROCESSED_{sample_file_info.name}"
        mock_storage.archive.assert_called_once_with(sample_file_info.id, expected_name)
