"""ドメイン固有の例外クラス"""


class SchoolAgentError(Exception):
    """School Agent の基底例外"""

    pass


class ConfigLoadError(SchoolAgentError):
    """設定読み込みエラー（Google Sheets等）"""

    pass


class FileDownloadError(SchoolAgentError):
    """ファイルダウンロードエラー"""

    pass


class AnalysisError(SchoolAgentError):
    """文書解析エラー（Gemini API等）"""

    pass


class ActionError(SchoolAgentError):
    """アクション実行エラー（Calendar/Todoist/Slack等）"""

    pass
