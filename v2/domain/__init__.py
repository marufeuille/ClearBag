"""Domain layer - 外部依存なしのドメインモデルとインターフェース定義"""

from v2.domain.errors import (
    ActionError,
    AnalysisError,
    ConfigLoadError,
    FileDownloadError,
    SchoolAgentError,
)
from v2.domain.models import (
    Category,
    DocumentAnalysis,
    EventData,
    FileInfo,
    ProcessingResult,
    Profile,
    Rule,
    TaskData,
)
from v2.domain.ports import (
    CalendarService,
    ConfigSource,
    DocumentAnalyzer,
    FileStorage,
    Notifier,
    TaskService,
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
