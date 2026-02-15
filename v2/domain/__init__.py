"""Domain layer - 外部依存なしのドメインモデルとインターフェース定義"""

from v2.domain.models import (
    Category,
    Profile,
    Rule,
    EventData,
    TaskData,
    DocumentAnalysis,
    FileInfo,
    ProcessingResult,
)
from v2.domain.errors import (
    SchoolAgentError,
    ConfigLoadError,
    FileDownloadError,
    AnalysisError,
    ActionError,
)
from v2.domain.ports import (
    ConfigSource,
    FileStorage,
    DocumentAnalyzer,
    CalendarService,
    TaskService,
    Notifier,
)

__all__ = [
    # Models
    "Category",
    "Profile",
    "Rule",
    "EventData",
    "TaskData",
    "DocumentAnalysis",
    "FileInfo",
    "ProcessingResult",
    # Errors
    "SchoolAgentError",
    "ConfigLoadError",
    "FileDownloadError",
    "AnalysisError",
    "ActionError",
    # Ports
    "ConfigSource",
    "FileStorage",
    "DocumentAnalyzer",
    "CalendarService",
    "TaskService",
    "Notifier",
]
