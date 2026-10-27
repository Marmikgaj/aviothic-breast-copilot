"""Unit and integration tests for Phase 7: Conversational Assistant, Safety Guardrails & Summaries.

Covers:
- Safety guardrails (non-diagnostic enforcement, mandatory disclaimer, citation check, off-context refusal)
- Prompt building and multi-report comparison detection
- Conversational chat turns and session memory updates
- Clinician and patient-friendly summary generation
- Structured session JSON export
- FastAPI endpoint integration tests (`/api/v1/sessions/{id}/chat`, `/summary`, `/export`)
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from src.api.app import create_app
from src.api.schemas import (
    BiomarkerEntity,
    BiradsEntity,
    ExtractedEntities,
    SourceSpan,
    TnmEntity,
    TumorDimensionEntity,
)
from src.context.schemas import (
    CitationReference,
    CitationSourceType,
    ConcordanceStatus,
    PatientContext,
    ProcessedReport,
    ReportModality,
)
from src.context.session_manager import SessionManager
from src.conversation.engine import ConversationEngine
from src.conversation.inference_client import MockInferenceClient
from src.conversation.prompt_builder import PromptBuilder, is_comparison_query
from src.conversation.schemas import ChatResponse
from src.core.config import get_settings
from src.reporting.generator import SummaryGenerator
from src.safety.guardrails import (
    MANDATORY_ASSISTIVE_DISCLAIMER,
    OFF_CONTEXT_REFUSAL,
    SafetyGuardrail,
)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provide headers with valid API key authentication."""
    settings = get_settings()
    return {"X-API-Key": settings.api_key}


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient instance."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_session_with_reports() -> PatientContext:
    """Provide a patient context with both mammography and biopsy reports."""
    ctx = PatientContext(session_id="test_sess_conv_001")

    mammo = ProcessedReport(
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

    path = ProcessedReport(
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

    ctx.reports.append(mammo)
    ctx.reports.append(path)
    return ctx


# ==============================================================================
# 1. Safety Guardrails Tests
# ==============================================================================


class TestSafetyGuardrail:
    """Test suite for safety guardrails and non-diagnostic boundary enforcement."""

    def test_off_context_query_detection(self) -> None:
        guard = SafetyGuardrail()
        assert guard.is_off_context_query("Write python code for a flask app") is True
        assert guard.is_off_context_query("What is the weather in New York?") is True
        assert guard.is_off_context_query("Can you tell me a joke?") is True
        assert guard.is_off_context_query("What does BI-RADS 4C mean in my mammogram?") is False

    def test_off_context_refusal_response(self) -> None:
        guard = SafetyGuardrail()
        result = guard.validate_and_guard(
            response="Here is some code",
            query="Write a script to scrape stocks",
        )
        assert result.is_safe is False
        assert result.is_off_context is True
        assert result.sanitized_response == OFF_CONTEXT_REFUSAL

    def test_diagnostic_leakage_detection_and_sanitization(self) -> None:
        guard = SafetyGuardrail()
        rogue_text = "I diagnose you with invasive ductal carcinoma. You definitely have cancer."
        violations = guard.check_diagnostic_leakage(rogue_text)
        assert len(violations) >= 1

        sanitized = guard.sanitize_diagnostic_leakage(rogue_text)
        assert "I diagnose you with" not in sanitized
        assert "You definitely have cancer" not in sanitized

    def test_mandatory_disclaimer_appended_if_missing(self) -> None:
        guard = SafetyGuardrail()
        text_without_disclaimer = "The report indicates a 15 mm lesion requiring biopsy [1]."
        result = guard.validate_and_guard(
            response=text_without_disclaimer,
            query="Explain the lesion",
            citations=[
                CitationReference(
                    source_type=CitationSourceType.REPORT,
                    source_id="rep_1",
                    text_snippet="15 mm lesion",
                )
            ],
        )
        assert MANDATORY_ASSISTIVE_DISCLAIMER in result.sanitized_response

    def test_citation_enforcement_on_clinical_claims(self) -> None:
        guard = SafetyGuardrail()
        text_with_claims = "Patient has BI-RADS 4C and should receive tamoxifen chemotherapy."
        # Without citations or inline brackets, should flag missing citation
        result = guard.validate_and_guard(
            response=text_with_claims,
            query="What treatment is recommended?",
            citations=[],
        )
        assert result.has_citations is False
        assert any("citation" in v.lower() for v in result.violations)


# ==============================================================================
# 2. Prompt Builder & Comparison Detection Tests
# ==============================================================================


class TestPromptBuilder:
    """Test suite for prompt building and cross-report comparison triggers."""

    def test_is_comparison_query(self) -> None:
        assert is_comparison_query("Compare the mammogram with the biopsy results") is True
        assert is_comparison_query("Is there concordance between both reports?") is True
        assert is_comparison_query("What is the difference between prior and current scans?") is True
        assert is_comparison_query("What does the tumor size mean?") is False

    def test_build_prompt_includes_comparison_instruction_when_multiple_reports(
        self, sample_session_with_reports: PatientContext
    ) -> None:
        builder = PromptBuilder()
        user_prompt, system_prompt = builder.build_prompt(
            context=sample_session_with_reports,
            query="Please compare the imaging findings with the biopsy pathology.",
        )
        assert "Special Instruction: The user is requesting a cross-report comparison" in system_prompt
        assert "Structured Clinical Findings" in user_prompt
        assert "4C" in user_prompt
        assert "pT1c" in user_prompt


# ==============================================================================
# 3. Conversation Engine Tests
# ==============================================================================


class TestConversationEngine:
    """Test suite for ConversationEngine execution and turn recording."""

    def test_chat_turn_execution_grounded(self, sample_session_with_reports: PatientContext) -> None:
        session_mgr = SessionManager()
        session_mgr._sessions[sample_session_with_reports.session_id] = sample_session_with_reports

        engine = ConversationEngine(
            session_manager=session_mgr,
            inference_client=MockInferenceClient(),
        )

        response: ChatResponse = engine.chat(
            session_id=sample_session_with_reports.session_id,
            message="What are the implications of the BI-RADS 4C category?",
        )

        assert response.session_id == sample_session_with_reports.session_id
        assert response.is_safe is True
        assert len(response.citations) > 0
        assert "BI-RADS Category" in response.response
        assert MANDATORY_ASSISTIVE_DISCLAIMER in response.response

        # Check session history was updated with user and assistant turns
        updated_session = session_mgr.get_session(sample_session_with_reports.session_id)
        assert updated_session is not None
        assert len(updated_session.history) == 2

    def test_chat_turn_off_context_refusal(self) -> None:
        session_mgr = SessionManager()
        engine = ConversationEngine(
            session_manager=session_mgr,
            inference_client=MockInferenceClient(),
        )

        response = engine.chat(
            session_id="test_sess_off",
            message="Write python code for a web scraper",
        )
        assert response.is_safe is False
        assert "specialized solely as an assistive breast cancer clinical copilot" in response.response

    def test_chat_turn_evaluates_multi_report_concordance(self, sample_session_with_reports: PatientContext) -> None:
        session_mgr = SessionManager()
        session_mgr._sessions[sample_session_with_reports.session_id] = sample_session_with_reports

        engine = ConversationEngine(
            session_manager=session_mgr,
            inference_client=MockInferenceClient(),
        )

        response = engine.chat(
            session_id=sample_session_with_reports.session_id,
            message="Compare both reports and assess concordance.",
        )
        assert response.concordance_status == ConcordanceStatus.CONCORDANT


# ==============================================================================
# 4. Summary Generator Tests
# ==============================================================================


class TestSummaryGenerator:
    """Test suite for clinician summary, patient guide, and JSON export."""

    def test_generate_clinician_summary(self, sample_session_with_reports: PatientContext) -> None:
        generator = SummaryGenerator()
        clinician_summary = generator.generate_clinician_summary(sample_session_with_reports)

        assert "CLINICAL ONCOLOGY MULTI-REPORT SUMMARY" in clinician_summary
        assert "DIAGNOSTIC TIMELINE" in clinician_summary
        assert "CONCORDANT" in clinician_summary
        assert "BI-RADS" in clinician_summary
        assert "pT1c" in clinician_summary
        assert "ER: positive" in clinician_summary
        assert MANDATORY_ASSISTIVE_DISCLAIMER in clinician_summary

    def test_generate_patient_summary(self, sample_session_with_reports: PatientContext) -> None:
        generator = SummaryGenerator()
        patient_summary = generator.generate_patient_summary(sample_session_with_reports)

        assert "UNDERSTANDING YOUR BREAST CARE REPORTS" in patient_summary
        assert "Mammogram" in patient_summary
        assert "Biopsy" in patient_summary
        assert "BI-RADS Category 4C" in patient_summary
        assert "Questions to Consider Asking Your Doctor" in patient_summary
        assert "NOT a medical diagnosis" in patient_summary
        assert MANDATORY_ASSISTIVE_DISCLAIMER in patient_summary

    def test_export_session_json(self, sample_session_with_reports: PatientContext) -> None:
        generator = SummaryGenerator()
        export = generator.export_session_json(sample_session_with_reports)

        assert export.session_id == sample_session_with_reports.session_id
        assert export.total_reports == 2
        assert "mammography" in export.modalities_present
        assert "pathology" in export.modalities_present
        assert export.concordance == ConcordanceStatus.CONCORDANT
        assert len(export.reports) == 2


# ==============================================================================
# 5. FastAPI Endpoints Integration Tests
# ==============================================================================


class TestSessionsApiEndpoints:
    """Integration tests for FastAPI /api/v1/sessions endpoints."""

    def test_chat_endpoint_valid_request(
        self,
        test_client: TestClient,
        auth_headers: dict[str, str],
        sample_session_with_reports: PatientContext,
    ) -> None:
        from src.context.session_manager import get_session_manager

        mgr = get_session_manager()
        mgr._sessions[sample_session_with_reports.session_id] = sample_session_with_reports

        payload = {
            "message": "What is the recommended next step for BI-RADS 4C?",
            "max_citations": 3,
        }
        resp = test_client.post(
            f"/api/v1/sessions/{sample_session_with_reports.session_id}/chat",
            json=payload,
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sample_session_with_reports.session_id
        assert "BI-RADS Category" in data["response"]
        assert len(data["citations"]) > 0
        assert data["is_safe"] is True

    def test_chat_endpoint_unauthorized(self, test_client: TestClient) -> None:
        resp = test_client.post(
            "/api/v1/sessions/sess_unauth/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 401

    def test_summary_endpoint_success(
        self,
        test_client: TestClient,
        auth_headers: dict[str, str],
        sample_session_with_reports: PatientContext,
    ) -> None:
        from src.context.session_manager import get_session_manager

        mgr = get_session_manager()
        mgr._sessions[sample_session_with_reports.session_id] = sample_session_with_reports

        resp = test_client.post(
            f"/api/v1/sessions/{sample_session_with_reports.session_id}/summary",
            json={"audience": "both"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sample_session_with_reports.session_id
        assert "CLINICAL ONCOLOGY" in data["clinician_summary"]
        assert "UNDERSTANDING YOUR BREAST CARE REPORTS" in data["patient_summary"]
        assert data["concordance_status"] == "concordant"

    def test_summary_endpoint_not_found(self, test_client: TestClient, auth_headers: dict[str, str]) -> None:
        resp = test_client.post(
            "/api/v1/sessions/non_existent_session_999/summary",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_export_endpoint_success(
        self,
        test_client: TestClient,
        auth_headers: dict[str, str],
        sample_session_with_reports: PatientContext,
    ) -> None:
        from src.context.session_manager import get_session_manager

        mgr = get_session_manager()
        mgr._sessions[sample_session_with_reports.session_id] = sample_session_with_reports

        resp = test_client.get(
            f"/api/v1/sessions/{sample_session_with_reports.session_id}/export",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sample_session_with_reports.session_id
        assert data["total_reports"] == 2
        assert data["concordance"] == "concordant"
        assert len(data["reports"]) == 2
