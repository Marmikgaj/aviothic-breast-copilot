"""Prompt assembly and conversational framing for clinical oncology reasoning.

Integrates patient context, RAG passages, and two-report comparison detection per PRD §4.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from src.context.schemas import PatientContext
from src.context.window_manager import ContextWindowManager
from src.rag.schemas import RetrievedPassage
from src.training.prompt_formatter import SYSTEM_PROMPT


def is_comparison_query(query: str) -> bool:
    """Detect if a user prompt is asking to compare or correlate findings across multiple reports."""
    comparison_patterns = [
        re.compile(r"\b(?:compare|comparison|difference|correlate|correlation|versus|vs\.?)\b", re.IGNORECASE),
        re.compile(
            r"\b(?:both\s+reports|between\s+(?:the\s+)?reports|prior\s+(?:report|scan|biopsy))\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:changes?\s+over\s+time|progression|evolution|concordance)\b", re.IGNORECASE),
    ]
    return any(p.search(query) for p in comparison_patterns)


class PromptBuilder:
    """Assembles prompt contexts and system framing for conversational assistant turns."""

    def __init__(self, window_manager: ContextWindowManager | None = None) -> None:
        self.window_manager = window_manager or ContextWindowManager()

    def build_prompt(
        self,
        context: PatientContext,
        query: str,
        retrieved_passages: Sequence[RetrievedPassage] = (),
    ) -> tuple[str, str]:
        """Build user prompt and system prompt for the inference engine.

        Args:
            context: The active patient session context.
            query: The user query.
            retrieved_passages: Retrieved guideline passages from RAG.

        Returns:
            Tuple of (user_prompt, system_prompt).
        """
        system = SYSTEM_PROMPT

        # Augment with comparison instructions if multiple reports and comparison query
        if len(context.reports) > 1 and is_comparison_query(query):
            system += (
                "\n\nSpecial Instruction: The user is requesting a cross-report comparison. "
                "Structure your response by comparing the imaging findings against the pathological results. "
                "Explicitly comment on radiologic-pathologic concordance or discordance."
            )

        assembled_context = self.window_manager.assemble_prompt_context(
            context=context,
            query=query,
            retrieved_passages=retrieved_passages,
        )

        return assembled_context, system
