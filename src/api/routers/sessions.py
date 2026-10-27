"""FastAPI router for conversational chat turns, report summaries, and session exports.

Implements Architecture §5 API contracts.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.context.session_manager import get_session_manager
from src.conversation.engine import get_conversation_engine
from src.conversation.schemas import ChatRequest, ChatResponse
from src.core.logging import get_logger
from src.reporting.generator import SummaryGenerator
from src.reporting.schemas import SessionExport, SummaryRequest, SummaryResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions & Chat"])


@router.post(
    "/{session_id}/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute grounded conversational turn",
    description="Processes a clinical query within a patient session, retrieving relevant guidelines and audit trails.",
)
async def chat_endpoint(session_id: str, request: ChatRequest) -> ChatResponse:
    """Execute a grounded chat turn within the specified patient session."""
    engine = get_conversation_engine()
    try:
        response = engine.chat(
            session_id=session_id,
            message=request.message,
            max_citations=request.max_citations,
        )
        return response
    except Exception as e:
        logger.error("Chat turn failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat execution failed: {e}",
        ) from e


@router.post(
    "/{session_id}/summary",
    response_model=SummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate clinician and patient-friendly summaries",
    description=(
        "Synthesizes all reports in the session into technical clinician notes and plain-language patient explanations."
    ),
)
async def summary_endpoint(session_id: str, request: SummaryRequest | None = None) -> SummaryResponse:
    """Generate multi-report clinician and patient-friendly summaries."""
    session_mgr = get_session_manager()
    session = session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient session '{session_id}' not found or has expired.",
        )

    generator = SummaryGenerator()
    return generator.generate_summary_response(session)


@router.get(
    "/{session_id}/export",
    response_model=SessionExport,
    status_code=status.HTTP_200_OK,
    summary="Export session data as structured JSON",
    description="Exports all reports, extracted entities with source spans, timeline events, and conversation turns.",
)
async def export_endpoint(session_id: str) -> SessionExport:
    """Export complete patient session history and audited clinical findings."""
    session_mgr = get_session_manager()
    session = session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient session '{session_id}' not found or has expired.",
        )

    generator = SummaryGenerator()
    return generator.export_session_json(session)
