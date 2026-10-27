"""Context window budgeting, intelligent truncation, and prompt assembly.

Ensures LLM inputs fit strictly within token budgets without dropping critical clinical facts
(BI-RADS, TNM staging, biomarkers) per PRD §4, Architecture §3, and Phases §6.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from src.context.schemas import ContextBudget, ConversationRole, PatientContext
from src.core.logging import get_logger
from src.rag.schemas import RetrievedPassage

logger = get_logger(__name__)


def estimate_tokens(text: str) -> int:
    """Estimate token count using the standard 4-characters-per-token heuristic.

    Args:
        text: Input string.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


class ContextWindowManager:
    """Manages token budgeting, content truncation, and prompt context assembly."""

    def __init__(self, budget: ContextBudget | None = None) -> None:
        """Initialize window manager with a token budget.

        Args:
            budget: Optional ContextBudget instance (defaults to 4096 total tokens).
        """
        self.budget = budget or ContextBudget()

    def build_clinical_facts_block(self, context: PatientContext) -> str:
        """Construct the immutable clinical facts block from structured extracted entities.

        This block has Priority 1 and is never dropped during truncation.
        """
        if not context.reports:
            return "No clinical reports uploaded in this session yet."

        lines: list[str] = ["### Structured Clinical Findings (Audited):"]
        for idx, report in enumerate(context.reports, 1):
            date_str = report.chronological_date
            modality_str = report.modality.value.upper()
            lines.append(f"• Report [{idx}] ({modality_str}, Date: {date_str}):")

            ents = report.entities
            has_ents = False
            for b in ents.birads:
                desc = f" ({b.descriptor})" if b.descriptor else ""
                lines.append(f"  - BI-RADS: {b.category}{desc} [Confidence: {b.confidence:.2f}]")
                has_ents = True
            for t in ents.tnm_staging:
                lines.append(f"  - TNM Stage: {t.raw_stage} [Confidence: {t.confidence:.2f}]")
                has_ents = True
            for bm in ents.biomarkers:
                status_label = str(bm.status)
                if bm.percentage is not None:
                    status_label += f" ({bm.percentage}%)"
                lines.append(f"  - Biomarker: {bm.name} {status_label} [Confidence: {bm.confidence:.2f}]")
                has_ents = True
            for td in ents.tumor_dimensions:
                dim_str = f"{td.primary_size_mm} mm" if td.primary_size_mm else "measured"
                lines.append(f"  - Tumor Size: {dim_str} [Confidence: {td.confidence:.2f}]")
                has_ents = True
            for ln in ents.lymph_nodes:
                if ln.nodes_examined is not None and ln.nodes_positive is not None:
                    ln_str = f"{ln.nodes_positive}/{ln.nodes_examined} positive"
                else:
                    ln_str = ln.span.snippet
                lines.append(f"  - Lymph Nodes: {ln_str} [Confidence: {ln.confidence:.2f}]")
                has_ents = True

            if not has_ents:
                lines.append("  - (No structured entities extracted)")

        return "\n".join(lines)

    def build_guideline_passages_block(self, passages: Sequence[RetrievedPassage], max_tokens: int) -> tuple[str, int]:
        """Format retrieved clinical guidelines within a specified token budget."""
        if not passages:
            return "No guideline passages retrieved.", 0

        lines: list[str] = ["### Retrieved Clinical Guidelines & Evidence:"]
        tokens_used = estimate_tokens(lines[0])

        for idx, passage in enumerate(passages, 1):
            passage_text = (
                f"Passage [{idx}] {passage.citation_label}:\n" f'"{passage.text}" (Relevance: {passage.score:.2f})'
            )
            p_tokens = estimate_tokens(passage_text)
            if tokens_used + p_tokens > max_tokens:
                logger.debug(
                    "Truncated retrieved passages due to token budget",
                    included=idx - 1,
                    total=len(passages),
                )
                break
            lines.append(passage_text)
            tokens_used += p_tokens

        return "\n\n".join(lines), tokens_used

    def build_conversation_history_block(self, context: PatientContext, max_tokens: int) -> tuple[str, int]:
        """Format recent conversation turns using a sliding window from newest to oldest."""
        if not context.history:
            return "", 0

        turns = context.history
        selected_turns: list[str] = []
        tokens_used = 0

        # Traverse backwards from most recent turn
        for turn in reversed(turns):
            role_label = "User" if turn.role == ConversationRole.USER else "Assistant"
            turn_str = f"{role_label}: {turn.content}"
            t_tokens = estimate_tokens(turn_str)

            if tokens_used + t_tokens > max_tokens:
                logger.debug("Truncated older conversation turns", kept=len(selected_turns), total=len(turns))
                break

            selected_turns.append(turn_str)
            tokens_used += t_tokens

        # Restore chronological order
        selected_turns.reverse()
        history_header = "### Prior Conversation Context:"
        result = history_header + "\n" + "\n".join(selected_turns)
        return result, tokens_used + estimate_tokens(history_header)

    def assemble_prompt_context(
        self,
        context: PatientContext,
        query: str,
        retrieved_passages: Sequence[RetrievedPassage] = (),
    ) -> str:
        """Assemble complete LLM input context respecting the token budget.

        Priority Ordering:
        1. Query + Immutable Structured Clinical Findings (Priority 1)
        2. Retrieved Guidelines / RAG Passages (Priority 2)
        3. Recent Conversation History (Priority 3)
        4. Raw Report Texts (Priority 4, truncated/condensed if budget requires)

        Args:
            context: Active session PatientContext.
            query: The user's prompt or clinical question.
            retrieved_passages: RAG passages retrieved for the query.

        Returns:
            Assembled, budget-compliant context string.
        """
        budget_limit = self.budget.available_context_tokens

        # 1. Query and Core Clinical Facts (Priority 1 - Mandatory)
        query_block = f"### Current Clinical Query:\n{query}"
        facts_block = self.build_clinical_facts_block(context)

        tokens_p1 = estimate_tokens(query_block) + estimate_tokens(facts_block)
        remaining_budget = max(0, budget_limit - tokens_p1)

        # 2. Retrieved Guidelines (Priority 2 - up to 40% of remaining budget)
        guideline_budget = int(remaining_budget * 0.40)
        guideline_block, tokens_g = self.build_guideline_passages_block(retrieved_passages, max_tokens=guideline_budget)
        remaining_budget = max(0, remaining_budget - tokens_g)

        # 3. Conversation History (Priority 3 - up to 35% of remaining budget)
        history_budget = int(remaining_budget * 0.50)
        history_block, tokens_h = self.build_conversation_history_block(context, max_tokens=history_budget)
        remaining_budget = max(0, remaining_budget - tokens_h)

        # 4. Report Raw Excerpts (Priority 4 - remaining budget)
        report_blocks: list[str] = []
        if remaining_budget > 64 and context.reports:
            report_blocks.append("### Report Text Excerpts:")
            for report in context.reports:
                header = f"--- {report.modality.value.upper()} ({report.chronological_date}) ---"
                excerpt = report.text[: remaining_budget * 3]  # truncate characters
                block = f"{header}\n{excerpt}"
                b_tokens = estimate_tokens(block)
                if b_tokens > remaining_budget:
                    break
                report_blocks.append(block)
                remaining_budget -= b_tokens

        sections = [facts_block]
        if report_blocks:
            sections.append("\n".join(report_blocks))
        if guideline_block and "No guideline passages" not in guideline_block:
            sections.append(guideline_block)
        if history_block:
            sections.append(history_block)
        sections.append(query_block)

        assembled = "\n\n".join(sections)
        logger.info(
            "Assembled prompt context",
            session_id=context.session_id,
            total_estimated_tokens=estimate_tokens(assembled),
            budget_limit=budget_limit,
        )
        return assembled
