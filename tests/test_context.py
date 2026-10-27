"""Unit and integration tests for session-scoped Patient Context and Memory (Phase 6).

Covers:
- In-memory session manager lifecycle and idle expiration
- Multi-report timeline aggregation and chronologic sorting
- Radiologic-pathologic concordance evaluation and discrepancy detection
- Context window budgeting and prioritized truncation
"""

from __future__ import annotations

import time

import pytest

from src.api.schemas import (
    BiomarkerEntity,
    BiradsEntity,
    ExtractedEntities,
    SourceSpan,
    TnmEntity,
    TumorDimensionEntity,
)
from src.context.aggregator import MultiReportAggregator
from src.context.schemas import (
    ConcordanceStatus,
    ConversationRole,
    ConversationTurn,
    PatientContext,
    ProcessedReport,
    ReportModality,
)
from src.context.session_manager import SessionManager
from src.context.window_manager import ContextWindowManager, estimate_tokens
from src.rag.schemas import GuidelineSource, RetrievedPassage


@pytest.fixture
def session_mgr() -> SessionManager:
    """Provide a fresh session manager for test isolation."""
    return SessionManager(default_ttl_seconds=3600)


@pytest.fixture
def sample_mammography_report() -> ProcessedReport:
    """Sample mammography report with BI-RADS 4C and mass findings."""
    return ProcessedReport(
        report_id="rep_mammo_001",
        modality=ReportModality.MAMMOGRAPHY,
        date_str="2026-03-10",
        text=(
            "Diagnostic mammogram demonstrates an irregular, spiculated 18 mm mass in the right breast upper outer "
            "quadrant. BI-RADS Category 4C: High suspicion for malignancy. Biopsy recommended."
        ),
        entities=ExtractedEntities(
            birads=[
                BiradsEntity(
                    category="4C",
                    descriptor="High suspicion for malignancy",
                    side="right",
                    span=SourceSpan(start_char=112, end_char=133, snippet="BI-RADS Category 4C"),
                    confidence=0.95,
                )
            ],
            tumor_dimensions=[
                TumorDimensionEntity(
                    primary_size_mm=18.0,
                    dimensions_mm=[18.0],
                    span=SourceSpan(start_char=59, end_char=64, snippet="18 mm"),
                    confidence=0.90,
                )
            ],
        ),
    )


@pytest.fixture
def sample_pathology_report_malignant() -> ProcessedReport:
    """Sample pathology biopsy report confirming invasive ductal carcinoma with biomarkers."""
    return ProcessedReport(
        report_id="rep_path_002",
        modality=ReportModality.PATHOLOGY,
        date_str="2026-03-17",
        text=(
            "Core needle biopsy of right breast: Invasive ductal carcinoma, histological grade 2. "
            "ER positive 95%, PR positive 80%, HER2 negative (IHC 1+), Ki-67 15%. pT1c."
        ),
        entities=ExtractedEntities(
            tnm_staging=[
                TnmEntity(
                    raw_stage="pT1c",
                    t_stage="pT1c",
                    is_pathological=True,
                    span=SourceSpan(start_char=145, end_char=149, snippet="pT1c"),
                    confidence=0.95,
                )
            ],
            biomarkers=[
                BiomarkerEntity(
                    name="ER",
                    status="positive",
                    percentage=95.0,
                    intensity="strong",
                    span=SourceSpan(start_char=85, end_char=100, snippet="ER positive 95%"),
                    confidence=0.95,
                ),
                BiomarkerEntity(
                    name="HER2",
                    status="negative",
                    ihc_score="1+",
                    span=SourceSpan(start_char=120, end_char=140, snippet="HER2 negative (IHC 1+)"),
                    confidence=0.95,
                ),
            ],
        ),
    )


@pytest.fixture
def sample_pathology_report_benign() -> ProcessedReport:
    """Sample pathology biopsy report reporting only benign fibrocystic changes."""
    return ProcessedReport(
        report_id="rep_path_benign_003",
        modality=ReportModality.PATHOLOGY,
        date_str="2026-03-18",
        text=(
            "Right breast core biopsy: Benign fibrocystic changes, apocrine metaplasia. "
            "No malignancy or atypical hyperplasia seen."
        ),
        entities=ExtractedEntities(),
    )


# ==============================================================================
# 1. Session Manager Tests
# ==============================================================================


class TestSessionManager:
    """Test suite for in-memory ephemeral SessionManager."""

    def test_create_and_get_session(self, session_mgr: SessionManager) -> None:
        session = session_mgr.create_session()
        assert session.session_id.startswith("sess_")
        assert len(session.reports) == 0
        assert len(session.history) == 0

        retrieved = session_mgr.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_create_session_with_custom_id(self, session_mgr: SessionManager) -> None:
        custom_id = "patient_session_xyz123"
        session = session_mgr.create_session(session_id=custom_id)
        assert session.session_id == custom_id

        retrieved = session_mgr.get_session(custom_id)
        assert retrieved is not None
        assert retrieved.session_id == custom_id

    def test_get_or_create_session(self, session_mgr: SessionManager) -> None:
        sid = "sess_auto_1"
        s1 = session_mgr.get_or_create_session(sid)
        assert s1.session_id == sid

        s2 = session_mgr.get_or_create_session(sid)
        assert s2.session_id == sid
        assert session_mgr.active_session_count() == 1

    def test_add_report_to_session(
        self, session_mgr: SessionManager, sample_mammography_report: ProcessedReport
    ) -> None:
        session = session_mgr.create_session()
        session_mgr.add_report(session.session_id, sample_mammography_report)

        retrieved = session_mgr.get_session(session.session_id)
        assert retrieved is not None
        assert len(retrieved.reports) == 1
        assert retrieved.reports[0].report_id == "rep_mammo_001"
        assert retrieved.get_report("rep_mammo_001") is not None

    def test_update_existing_report_replaces_in_session(
        self, session_mgr: SessionManager, sample_mammography_report: ProcessedReport
    ) -> None:
        session = session_mgr.create_session()
        session_mgr.add_report(session.session_id, sample_mammography_report)

        # Update with new text
        updated = sample_mammography_report.model_copy(update={"text": "Updated text"})
        session_mgr.add_report(session.session_id, updated)

        retrieved = session_mgr.get_session(session.session_id)
        assert retrieved is not None
        assert len(retrieved.reports) == 1
        assert retrieved.reports[0].text == "Updated text"

    def test_add_turn_to_session(self, session_mgr: SessionManager) -> None:
        session = session_mgr.create_session()
        turn = ConversationTurn(
            role=ConversationRole.USER,
            content="Can you explain what BI-RADS 4C means in my report?",
        )
        session_mgr.add_turn(session.session_id, turn)

        retrieved = session_mgr.get_session(session.session_id)
        assert retrieved is not None
        assert len(retrieved.history) == 1
        assert retrieved.history[0].content == turn.content

    def test_session_idle_expiration(self) -> None:
        # Fast TTL for test
        mgr = SessionManager(default_ttl_seconds=0)
        session = mgr.create_session()
        time.sleep(0.01)

        # Should be None due to expiration
        assert mgr.get_session(session.session_id) is None
        assert mgr.active_session_count() == 0

    def test_delete_session(self, session_mgr: SessionManager) -> None:
        session = session_mgr.create_session()
        assert session_mgr.active_session_count() == 1

        deleted = session_mgr.delete_session(session.session_id)
        assert deleted is True
        assert session_mgr.get_session(session.session_id) is None
        assert session_mgr.active_session_count() == 0

    def test_session_isolation_no_leakage(
        self,
        session_mgr: SessionManager,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_malignant: ProcessedReport,
    ) -> None:
        s1 = session_mgr.create_session(session_id="sess_1")
        s2 = session_mgr.create_session(session_id="sess_2")

        session_mgr.add_report("sess_1", sample_mammography_report)
        session_mgr.add_report("sess_2", sample_pathology_report_malignant)

        # S1 must not see S2's reports
        assert len(s1.reports) == 1
        assert s1.reports[0].report_id == "rep_mammo_001"
        assert len(s2.reports) == 1
        assert s2.reports[0].report_id == "rep_path_002"


# ==============================================================================
# 2. Multi-Report Aggregator & Concordance Tests
# ==============================================================================


class TestMultiReportAggregator:
    """Test suite for MultiReportAggregator, timelines, and concordance logic."""

    def test_chronological_ordering(
        self,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_malignant: ProcessedReport,
    ) -> None:
        # Add pathology first, then mammography
        ctx = PatientContext(reports=[sample_pathology_report_malignant, sample_mammography_report])
        aggregator = MultiReportAggregator(ctx)

        sorted_reports = aggregator.get_chronological_reports()
        assert len(sorted_reports) == 2
        # Mammography (March 10) must precede pathology (March 17)
        assert sorted_reports[0].report_id == "rep_mammo_001"
        assert sorted_reports[1].report_id == "rep_path_002"

    def test_aggregate_entities(
        self,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_malignant: ProcessedReport,
    ) -> None:
        ctx = PatientContext(reports=[sample_mammography_report, sample_pathology_report_malignant])
        aggregator = MultiReportAggregator(ctx)

        entities = aggregator.aggregate_entities()
        assert len(entities.birads) == 1
        assert entities.birads[0].category == "4C"
        assert len(entities.tnm_staging) == 1
        assert entities.tnm_staging[0].raw_stage == "pT1c"
        assert len(entities.biomarkers) == 2
        assert len(entities.tumor_dimensions) == 1

    def test_build_timeline(
        self,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_malignant: ProcessedReport,
    ) -> None:
        ctx = PatientContext(reports=[sample_mammography_report, sample_pathology_report_malignant])
        aggregator = MultiReportAggregator(ctx)

        timeline = aggregator.build_timeline()
        assert len(timeline) == 2
        assert timeline[0].modality == ReportModality.MAMMOGRAPHY
        assert timeline[0].birads_category == "4C"
        assert timeline[1].modality == ReportModality.PATHOLOGY
        assert timeline[1].tnm_stage == "pT1c"
        assert "ER" in timeline[1].biomarkers

    def test_concordance_high_suspicion_confirmed_is_concordant(
        self,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_malignant: ProcessedReport,
    ) -> None:
        # BI-RADS 4C + Invasive ductal carcinoma
        ctx = PatientContext(reports=[sample_mammography_report, sample_pathology_report_malignant])
        aggregator = MultiReportAggregator(ctx)

        status, notes = aggregator.evaluate_concordance()
        assert status == ConcordanceStatus.CONCORDANT
        assert any("Concordant" in n for n in notes)

    def test_concordance_high_suspicion_benign_is_discordant(
        self,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_benign: ProcessedReport,
    ) -> None:
        # BI-RADS 4C + Benign fibrocystic changes without lesion
        ctx = PatientContext(reports=[sample_mammography_report, sample_pathology_report_benign])
        aggregator = MultiReportAggregator(ctx)

        status, notes = aggregator.evaluate_concordance()
        assert status == ConcordanceStatus.DISCORDANT
        assert any("Discordance Alert" in n for n in notes)

    def test_concordance_single_report_is_not_applicable(self, sample_mammography_report: ProcessedReport) -> None:
        ctx = PatientContext(reports=[sample_mammography_report])
        aggregator = MultiReportAggregator(ctx)

        status, _notes = aggregator.evaluate_concordance()
        assert status == ConcordanceStatus.NOT_APPLICABLE

    def test_generate_summary_structure(
        self,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_malignant: ProcessedReport,
    ) -> None:
        ctx = PatientContext(reports=[sample_mammography_report, sample_pathology_report_malignant])
        aggregator = MultiReportAggregator(ctx)

        summary = aggregator.generate_summary()
        assert summary.total_reports == 2
        assert ReportModality.MAMMOGRAPHY in summary.modalities_present
        assert ReportModality.PATHOLOGY in summary.modalities_present
        assert summary.concordance == ConcordanceStatus.CONCORDANT
        assert len(summary.timeline) == 2


# ==============================================================================
# 3. Context Window Manager & Prompt Budgeting Tests
# ==============================================================================


class TestContextWindowManager:
    """Test suite for ContextWindowManager, token budgeting, and prioritized truncation."""

    def test_estimate_tokens(self) -> None:
        assert estimate_tokens("") == 0
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("a" * 100) == 25

    def test_build_clinical_facts_block_preserves_entities(
        self,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_malignant: ProcessedReport,
    ) -> None:
        ctx = PatientContext(reports=[sample_mammography_report, sample_pathology_report_malignant])
        wm = ContextWindowManager()

        facts = wm.build_clinical_facts_block(ctx)
        assert "4C" in facts
        assert "pT1c" in facts
        assert "MAMMOGRAPHY" in facts
        assert "PATHOLOGY" in facts

    def test_guideline_passages_budget_truncation(self) -> None:
        wm = ContextWindowManager()
        passages = [
            RetrievedPassage(
                id=f"doc_{i}",
                document_id=f"doc_{i}",
                text="Guideline recommendation on oncology treatment " * 10,
                score=0.9 - (i * 0.1),
                citation_label=f"[NCCN Guide {i}]",
                title=f"NCCN Clinical Practice Guideline {i}",
                source=GuidelineSource.NCCN,
            )
            for i in range(10)
        ]

        # Give a small budget that can only fit 1-2 passages
        block, tokens = wm.build_guideline_passages_block(passages, max_tokens=300)
        assert tokens <= 300
        assert "Passage [1]" in block
        # Passage 9 must have been truncated
        assert "Passage [9]" not in block

    def test_conversation_history_sliding_window(self) -> None:
        wm = ContextWindowManager()
        ctx = PatientContext()
        for i in range(10):
            role = ConversationRole.USER if i % 2 == 0 else ConversationRole.ASSISTANT
            ctx.history.append(ConversationTurn(role=role, content=f"Message turn number {i} with some content"))

        # Budget allowing only the last ~2-3 turns
        block, tokens = wm.build_conversation_history_block(ctx, max_tokens=60)
        assert tokens <= 100
        # Newest turn (9) must be preserved
        assert "Message turn number 9" in block

    def test_assemble_prompt_context_contains_all_core_sections(
        self,
        sample_mammography_report: ProcessedReport,
        sample_pathology_report_malignant: ProcessedReport,
    ) -> None:
        ctx = PatientContext(reports=[sample_mammography_report, sample_pathology_report_malignant])
        ctx.history.append(
            ConversationTurn(
                role=ConversationRole.USER,
                content="What should we do about the mass?",
            )
        )
        passages = [
            RetrievedPassage(
                id="doc_1",
                document_id="doc_1",
                text="NCCN guidelines state that BI-RADS 4C requires biopsy.",
                score=0.92,
                citation_label="[NCCN Guidelines 2024]",
                title="NCCN Breast Cancer Screening and Diagnosis Guidelines",
                source=GuidelineSource.NCCN,
            )
        ]

        wm = ContextWindowManager()
        prompt = wm.assemble_prompt_context(
            context=ctx,
            query="Explain the stage and biomarker implications.",
            retrieved_passages=passages,
        )

        # Priority 1: Clinical findings and query must be present
        assert "Structured Clinical Findings" in prompt
        assert "4C" in prompt
        assert "pT1c" in prompt
        assert "Current Clinical Query" in prompt
        assert "Explain the stage and biomarker implications." in prompt

        # Priority 2 & 3: Guidelines and history
        assert "Retrieved Clinical Guidelines" in prompt
        assert "What should we do about the mass?" in prompt

        # Ensure budget is maintained
        assert estimate_tokens(prompt) < wm.budget.available_context_tokens
