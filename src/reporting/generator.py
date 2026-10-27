"""Clinical and patient-friendly summary generation and structured JSON export engine.

Complies with PRD §3, PRD §4 (clinician review requirement), and Rules.md §8.
"""

from __future__ import annotations

from typing import Any

from src.context.aggregator import MultiReportAggregator
from src.context.schemas import ConcordanceStatus, PatientContext
from src.core.logging import get_logger
from src.reporting.schemas import SessionExport, SummaryResponse
from src.safety.guardrails import MANDATORY_ASSISTIVE_DISCLAIMER

logger = get_logger(__name__)


class SummaryGenerator:
    """Generates technical clinician summaries, plain-language patient summaries, and JSON exports."""

    def generate_clinician_summary(self, context: PatientContext) -> str:
        """Generate a dense, technical clinical summary suitable for EHR notes and dictations."""
        if not context.reports:
            return "No clinical reports available in this session for summary generation."

        aggregator = MultiReportAggregator(context)
        summary = aggregator.generate_summary()

        sections: list[str] = [
            "CLINICAL ONCOLOGY MULTI-REPORT SUMMARY",
            "=======================================",
            f"Session ID: {context.session_id}",
            f"Total Reports: {summary.total_reports}",
            f"Modalities Covered: {', '.join(m.value.upper() for m in summary.modalities_present)}",
            "",
            "1. DIAGNOSTIC TIMELINE & FINDINGS:",
        ]

        for entry in summary.timeline:
            sections.append(f"• [{entry.date_str}] {entry.modality.value.upper()} (Report ID: {entry.report_id})")
            for finding in entry.key_findings:
                sections.append(f"    - {finding}")

        sections.extend(
            [
                "",
                "2. RADIOLOGIC-PATHOLOGIC CONCORDANCE:",
                f"• Status: {summary.concordance.value.upper()}",
            ]
        )
        for note in summary.concordance_notes:
            sections.append(f"  Note: {note}")

        sections.extend(
            [
                "",
                "3. AUDITED CLINICAL ENTITIES SUMMARY:",
            ]
        )
        ents = summary.aggregated_entities
        if ents.birads:
            sections.append(
                f"• BI-RADS Assessment: {', '.join(f'Category {b.category} ({b.side})' for b in ents.birads)}"
            )
        if ents.tnm_staging:
            sections.append(f"• Pathological Staging: {', '.join(t.raw_stage for t in ents.tnm_staging)}")
        if ents.biomarkers:
            bm_strs = []
            for bm in ents.biomarkers:
                detail: str = str(bm.status)
                if bm.percentage is not None:
                    detail += f" ({bm.percentage}%)"
                elif bm.ihc_score:
                    detail += f" (IHC {bm.ihc_score})"
                bm_strs.append(f"{bm.name}: {detail}")
            sections.append(f"• Biomarkers: {'; '.join(bm_strs)}")
        if ents.tumor_dimensions:
            dim_strs = [f"{td.primary_size_mm} mm" for td in ents.tumor_dimensions if td.primary_size_mm]
            if dim_strs:
                sections.append(f"• Primary Dimensions: {', '.join(dim_strs)}")
        if ents.lymph_nodes:
            ln_strs = [
                f"{ln.nodes_positive}/{ln.nodes_examined} positive"
                for ln in ents.lymph_nodes
                if ln.nodes_examined is not None and ln.nodes_positive is not None
            ]
            if ln_strs:
                sections.append(f"• Nodal Involvement: {', '.join(ln_strs)}")

        sections.extend(
            [
                "",
                "4. CLINICAL MANAGEMENT CONSIDERATIONS (GUIDELINE-BASED):",
                "• Multidisciplinary tumor board review recommended.",
                "• Correlation of pathological margins and receptor profile with definitive surgical planning.",
                "",
                MANDATORY_ASSISTIVE_DISCLAIMER,
            ]
        )

        return "\n".join(sections)

    def generate_patient_summary(self, context: PatientContext) -> str:
        """Generate a plain-language summary for the clinician to review and share with the patient.

        Per PRD §4: Generated exclusively for clinician mediation, never sent directly to a patient.
        """
        if not context.reports:
            return (
                "No reports have been uploaded to this session yet.\n\n"
                "Please speak directly with your doctor regarding your care."
            )

        aggregator = MultiReportAggregator(context)
        summary = aggregator.generate_summary()

        paragraphs: list[str] = [
            "UNDERSTANDING YOUR BREAST CARE REPORTS",
            "A Patient Guide (To Be Reviewed With Your Doctor)",
            "--------------------------------------------------",
            "This guide translates the medical terms from your recent imaging and lab reports into everyday "
            "language to help you prepare for discussions with your healthcare team.",
            "",
            "What Tests Were Reviewed:",
        ]

        for entry in summary.timeline:
            modality_friendly = {
                "mammography": "Mammogram (X-ray picture of the breast)",
                "ultrasound": "Breast Ultrasound (sound-wave scan)",
                "pathology": "Biopsy / Pathology Lab Report (examination of cells under a microscope)",
                "mri": "Breast MRI (detailed magnetic imaging)",
            }.get(entry.modality.value, entry.modality.value.title())
            paragraphs.append(f"• {modality_friendly} on {entry.date_str}")

        paragraphs.extend(
            [
                "",
                "Key Findings Explained in Plain Language:",
            ]
        )

        ents = summary.aggregated_entities
        if ents.birads:
            for b in ents.birads:
                cat = b.category
                if cat in {"1", "2"}:
                    explanation = "Routine or benign findings; no suspicious areas were noted."
                elif cat == "3":
                    explanation = "Findings are very likely benign; usually short-term follow-up imaging is suggested."
                elif cat in {"4", "4A", "4B", "4C"}:
                    explanation = (
                        "An area was found that requires a small tissue sample (biopsy) to examine more closely."
                    )
                elif cat == "5":
                    explanation = "Findings strongly suggest an area that needs definitive biopsy confirmation."
                else:
                    explanation = "Imaging assessment noted for review."
                paragraphs.append(f"• BI-RADS Category {cat}: {explanation}")

        if ents.biomarkers:
            paragraphs.append("")
            paragraphs.append("Hormone Receptors & Protein Tests (Biomarkers):")
            for bm in ents.biomarkers:
                if bm.name in {"ER", "PR"}:
                    paragraphs.append(
                        f"• {bm.name} ({bm.status.title()}): Tests whether tumor cells respond to hormone signals. "
                        "When positive, treatments that balance hormones can be very effective."
                    )
                elif bm.name == "HER2":
                    paragraphs.append(
                        f"• HER2 ({bm.status.title()}): Tests for a specific growth protein. "
                        "Specialized targeted medicines are available when this marker is present."
                    )

        if summary.concordance == ConcordanceStatus.CONCORDANT:
            paragraphs.extend(
                [
                    "",
                    "How the Results Match Up:",
                    "• The imaging and lab biopsy findings agree with each other, providing a clear picture for your "
                    "care team.",
                ]
            )
        elif summary.concordance == ConcordanceStatus.DISCORDANT:
            paragraphs.extend(
                [
                    "",
                    "How the Results Match Up:",
                    "• The imaging findings and the lab biopsy results showed differences that your doctor will want "
                    "to review closely to decide if any additional test or repeat sample is needed.",
                ]
            )

        paragraphs.extend(
            [
                "",
                "Questions to Consider Asking Your Doctor:",
                "1. What do these test results mean for my specific treatment plan?",
                "2. Are any additional tests or follow-up scans recommended?",
                "3. What are the next steps in my care?",
                "",
                "IMPORTANT NOTICE FOR PATIENTS:",
                "This document is an AI-assisted plain-language guide intended for your doctor to review with you. "
                "It is NOT a medical diagnosis. Only your physician can diagnose medical conditions and recommend "
                "treatment plans.",
                "",
                MANDATORY_ASSISTIVE_DISCLAIMER,
            ]
        )

        return "\n".join(paragraphs)

    def generate_summary_response(self, context: PatientContext) -> SummaryResponse:
        """Produce structured SummaryResponse with both clinician and patient views."""
        aggregator = MultiReportAggregator(context)
        summary = aggregator.generate_summary()

        clinician_text = self.generate_clinician_summary(context)
        patient_text = self.generate_patient_summary(context)

        return SummaryResponse(
            session_id=context.session_id,
            clinician_summary=clinician_text,
            patient_summary=patient_text,
            concordance_status=summary.concordance,
            timeline=summary.timeline,
            disclaimer=MANDATORY_ASSISTIVE_DISCLAIMER,
        )

    def export_session_json(self, context: PatientContext) -> SessionExport:
        """Export the entire patient session as structured, auditable JSON."""
        aggregator = MultiReportAggregator(context)
        summary = aggregator.generate_summary()

        reports_data: list[dict[str, Any]] = []
        for r in context.reports:
            reports_data.append(
                {
                    "report_id": r.report_id,
                    "modality": r.modality.value,
                    "date": r.chronological_date,
                    "ocr_confidence": r.ocr_confidence,
                    "entities": r.entities.model_dump(),
                    "raw_text_length": len(r.text),
                }
            )

        history_data: list[dict[str, Any]] = []
        for turn in context.history:
            history_data.append(
                {
                    "turn_id": turn.turn_id,
                    "role": turn.role.value,
                    "content": turn.content,
                    "citations": [c.model_dump() for c in turn.citations],
                    "timestamp": turn.timestamp.isoformat(),
                }
            )

        return SessionExport(
            session_id=context.session_id,
            created_at=context.created_at.isoformat(),
            updated_at=context.updated_at.isoformat(),
            total_reports=len(context.reports),
            modalities_present=[m.value for m in summary.modalities_present],
            concordance=summary.concordance,
            concordance_notes=summary.concordance_notes,
            timeline=summary.timeline,
            reports=reports_data,
            conversation_history=history_data,
            metadata=context.metadata,
        )
