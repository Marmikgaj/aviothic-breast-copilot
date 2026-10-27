"""Session-scoped Patient Context and Memory management.

Provides in-memory session tracking, multi-report timeline aggregation,
radiologic-pathologic concordance evaluation, and context window budgeting.
"""

from src.context.aggregator import MultiReportAggregator
from src.context.schemas import (
    CitationReference,
    CitationSourceType,
    ConcordanceStatus,
    ContextBudget,
    ConversationRole,
    ConversationTurn,
    MultiReportSummary,
    MultiReportTimelineEntry,
    PatientContext,
    ProcessedReport,
    ReportModality,
)
from src.context.session_manager import SessionManager, get_session_manager
from src.context.window_manager import ContextWindowManager, estimate_tokens

__all__ = [
    "CitationReference",
    "CitationSourceType",
    "ConcordanceStatus",
    "ContextBudget",
    "ContextWindowManager",
    "ConversationRole",
    "ConversationTurn",
    "MultiReportAggregator",
    "MultiReportSummary",
    "MultiReportTimelineEntry",
    "PatientContext",
    "ProcessedReport",
    "ReportModality",
    "SessionManager",
    "estimate_tokens",
    "get_session_manager",
]
