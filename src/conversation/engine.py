"""Full conversational assistant engine orchestrating RAG, LLM inference, and safety guardrails.

Implements Phase 7 deliverable per PRD §4, Architecture §5, and Rules.md.
"""

from __future__ import annotations

import time

from src.context.aggregator import MultiReportAggregator
from src.context.schemas import (
    CitationReference,
    CitationSourceType,
    ConversationRole,
    ConversationTurn,
)
from src.context.session_manager import SessionManager, get_session_manager
from src.conversation.inference_client import BaseInferenceClient, get_inference_client
from src.conversation.prompt_builder import PromptBuilder
from src.conversation.schemas import ChatResponse
from src.core.logging import get_logger
from src.rag.retriever import OncologyRetriever
from src.safety.guardrails import SafetyGuardrail

logger = get_logger(__name__)


class ConversationEngine:
    """Orchestrates grounded conversational chat turns within patient sessions."""

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        retriever: OncologyRetriever | None = None,
        inference_client: BaseInferenceClient | None = None,
        guardrail: SafetyGuardrail | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.session_manager = session_manager or get_session_manager()
        self.retriever = retriever or OncologyRetriever()
        self.inference_client = inference_client or get_inference_client()
        self.guardrail = guardrail or SafetyGuardrail()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def chat(self, session_id: str, message: str, max_citations: int = 3) -> ChatResponse:
        """Execute a grounded conversational turn within a patient session.

        Args:
            session_id: Active session ID.
            message: User query or prompt.
            max_citations: Maximum grounding citations to bind.

        Returns:
            ChatResponse with safety-audited answer, citations, and concordance status.
        """
        start_time = time.perf_counter()
        session = self.session_manager.get_or_create_session(session_id)

        # 1. Check off-context guardrail
        if self.guardrail.is_off_context_query(message):
            guard_result = self.guardrail.validate_and_guard(
                response="",
                query=message,
                context=session,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            turn = ConversationTurn(role=ConversationRole.USER, content=message)
            self.session_manager.add_turn(session_id, turn)
            resp_turn = ConversationTurn(role=ConversationRole.ASSISTANT, content=guard_result.sanitized_response)
            self.session_manager.add_turn(session_id, resp_turn)

            return ChatResponse(
                session_id=session_id,
                turn_id=resp_turn.turn_id,
                response=guard_result.sanitized_response,
                citations=[],
                concordance_status=None,
                is_safe=False,
                latency_ms=round(elapsed_ms, 2),
            )

        # 2. RAG Retrieval grounded in query and session entities
        rag_result = self.retriever.retrieve(message)
        passages = rag_result.passages[:max_citations]

        # Convert passages to CitationReference models
        citations: list[CitationReference] = []
        for p in passages:
            citations.append(
                CitationReference(
                    source_type=CitationSourceType.GUIDELINE,
                    source_id=p.citation_label,
                    text_snippet=p.text[:140] + ("..." if len(p.text) > 140 else ""),
                    retrieval_score=p.score,
                    guideline_source=p.source,
                )
            )

        # Add report source citation if reports exist in session
        for rep in session.reports:
            citations.append(
                CitationReference(
                    source_type=CitationSourceType.REPORT,
                    source_id=rep.report_id,
                    text_snippet=f"{rep.modality.value.upper()} report from {rep.chronological_date}",
                    retrieval_score=1.0,
                )
            )

        # 3. Check concordance if multi-report session
        concordance_status = None
        if len(session.reports) > 1:
            aggregator = MultiReportAggregator(session)
            concordance_status, _notes = aggregator.evaluate_concordance()

        # 4. Prompt Assembly & Inference
        user_prompt, system_prompt = self.prompt_builder.build_prompt(
            context=session,
            query=message,
            retrieved_passages=passages,
        )

        raw_response = self.inference_client.generate(user_prompt, system_prompt)

        # 5. Safety Guardrails & Non-Diagnostic Audit
        guard_result = self.guardrail.validate_and_guard(
            response=raw_response,
            query=message,
            context=session,
            citations=citations,
        )

        # 6. Record turns in session history
        user_turn = ConversationTurn(role=ConversationRole.USER, content=message)
        self.session_manager.add_turn(session_id, user_turn)

        asst_turn = ConversationTurn(
            role=ConversationRole.ASSISTANT,
            content=guard_result.sanitized_response,
            citations=citations,
        )
        self.session_manager.add_turn(session_id, asst_turn)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            "Completed conversational chat turn",
            session_id=session_id,
            turn_id=asst_turn.turn_id,
            latency_ms=round(elapsed_ms, 2),
            citations_count=len(citations),
            is_safe=guard_result.is_safe,
        )

        return ChatResponse(
            session_id=session_id,
            turn_id=asst_turn.turn_id,
            response=guard_result.sanitized_response,
            citations=citations,
            concordance_status=concordance_status,
            is_safe=guard_result.is_safe,
            latency_ms=round(elapsed_ms, 2),
        )


# Singleton instance
_engine: ConversationEngine | None = None


def get_conversation_engine() -> ConversationEngine:
    """Return the ConversationEngine singleton instance."""
    global _engine
    if _engine is None:
        _engine = ConversationEngine()
    return _engine
