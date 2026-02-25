"""DocumentProcessor のユニットテスト"""

import logging
from unittest.mock import MagicMock

import pytest
from v2.domain.models import Profile, Rule
from v2.domain.ports import DocumentAnalyzer
from v2.services.document_processor import DocumentProcessor


@pytest.fixture
def mock_analyzer(sample_analysis) -> MagicMock:
    """DocumentAnalyzer のモック（DocumentProcessorテスト用）"""
    mock = MagicMock(spec=DocumentAnalyzer)
    mock.analyze.return_value = sample_analysis
    return mock


@pytest.fixture
def processor(mock_analyzer) -> DocumentProcessor:
    """DocumentProcessor のインスタンス"""
    return DocumentProcessor(analyzer=mock_analyzer)


class TestDocumentProcessor:
    """DocumentProcessor の単体テスト"""

    def test_process_returns_document_analysis(
        self, processor, mock_analyzer, sample_profiles, sample_analysis
    ):
        """process() が DocumentAnalysis を返す"""
        content = b"fake-pdf-content"
        mime_type = "application/pdf"
        rules: list[Rule] = []

        result = processor.process(content, mime_type, sample_profiles, rules)

        assert result == sample_analysis
        mock_analyzer.analyze.assert_called_once_with(
            content, mime_type, sample_profiles, rules
        )

    def test_process_passes_profiles_and_rules(self, processor, mock_analyzer):
        """process() が profiles と rules を analyzer に正しく渡す"""
        content = b"data"
        mime_type = "image/jpeg"
        profiles = {
            "P1": Profile(
                id="P1",
                name="テスト",
                grade="小1",
                keywords="",
                calendar_id="",
            )
        }
        rules = [Rule(rule_id="R1", target_profile="ALL", rule_type="INFO", content="test")]

        processor.process(content, mime_type, profiles, rules)

        mock_analyzer.analyze.assert_called_once_with(content, mime_type, profiles, rules)

    def test_process_reraises_analyzer_exception(self, processor, mock_analyzer):
        """analyzer が例外を投げた場合、process() も例外を再送出する"""
        mock_analyzer.analyze.side_effect = RuntimeError("Gemini API error")

        with pytest.raises(RuntimeError, match="Gemini API error"):
            processor.process(b"data", "application/pdf", {}, [])

    def test_process_logs_on_start_and_completion(
        self, processor, sample_profiles, caplog
    ):
        """process() が開始ログと完了ログを出力する"""
        with caplog.at_level(logging.INFO, logger="v2.services.document_processor"):
            processor.process(b"test", "application/pdf", sample_profiles, [])

        messages = [r.getMessage() for r in caplog.records]
        # 開始ログ
        assert any("Processing document" in m for m in messages)
        # 完了ログ
        assert any("Processing complete" in m for m in messages)

    def test_process_logs_error_on_failure(self, processor, mock_analyzer, caplog):
        """analyzer が例外を投げた場合、エラーログが出力される"""
        mock_analyzer.analyze.side_effect = ValueError("bad input")

        with caplog.at_level(logging.ERROR, logger="v2.services.document_processor"), pytest.raises(ValueError):
            processor.process(b"data", "application/pdf", {}, [])

        assert any("Document processing failed" in r.getMessage() for r in caplog.records)
