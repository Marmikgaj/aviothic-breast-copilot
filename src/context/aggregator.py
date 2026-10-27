"""Multi-report aggregation, temporal timeline construction, and concordance evaluation.

Synthesizes multiple imaging and pathology reports for a single patient session
per PRD §4, Architecture §4, and clinical guidelines.
"""

from __future__ import annotations

from src.api.schemas import ExtractedEntities
from src.context.schemas import (
    ConcordanceStatus,
    MultiReportSummary,
    MultiReportTimelineEntry,
    PatientContext,
    ProcessedReport,
    ReportModality,
)
from src.core.logging import get_logger

logger = get_logger(__name__)

# Keywords indicating malignant or premalignant histology on pathology
_MALIGNANCY_HISTOLOGY_TERMS = {
    "invasive ductal",
    "invasive lobular",
    "carcinoma",
    "dcis",
    "ductal carcinoma in situ",
    "lcis",
    "lobular carcinoma in situ",
    "malignant",
    "atypical ductal hyperplasia",
    "adh",
    "adenocarcinoma",
}

# Keywords indicating strictly benign histology
_BENIGN_HISTOLOGY_TERMS = {
    "fibroadenoma",
    "fibrocystic",
    "cyst",
    "benign",
    "usual ductal hyperplasia",
    "apocrine metaplasia",
    "sclerosing adenosis",
    "no malignancy",
    "negative for malignancy",
}


class MultiReportAggregator:
    """Aggregates and synthesizes multiple clinical reports in a patient context session."""

    def __init__(self, context: PatientContext) -> None:
        """Initialize aggregator with a PatientContext.

        Args:
            context: The patient context containing uploaded reports.
        """
        self.context = context

    def get_chronological_reports(self) -> list[ProcessedReport]:
        """Return reports sorted chronologically by examination or upload date."""
        return sorted(self.context.reports, key=lambda r: r.chronological_date)

    def aggregate_entities(self) -> ExtractedEntities:
        """Aggregate all extracted clinical entities across all reports in chronological order."""
        sorted_reports = self.get_chronological_reports()
        aggregated = ExtractedEntities()
        for report in sorted_reports:
            aggregated.birads.extend(report.entities.birads)
            aggregated.tnm_staging.extend(report.entities.tnm_staging)
            aggregated.biomarkers.extend(report.entities.biomarkers)
            aggregated.tumor_dimensions.extend(report.entities.tumor_dimensions)
            aggregated.lymph_nodes.extend(report.entities.lymph_nodes)
        return aggregated

    def build_timeline(self) -> list[MultiReportTimelineEntry]:
        """Construct a diagnostic timeline tracking findings over time across all reports."""
        timeline: list[MultiReportTimelineEntry] = []
        sorted_reports = self.get_chronological_reports()

        for report in sorted_reports:
            findings: list[str] = []
            birads_val: str | None = None
            tnm_val: str | None = None
            biomarkers: dict[str, str] = {}

            for b in report.entities.birads:
                birads_val = b.category
                desc = f" ({b.descriptor})" if b.descriptor else ""
                findings.append(f"BI-RADS: {b.category}{desc}")

            for t in report.entities.tnm_staging:
                tnm_val = t.raw_stage
                findings.append(f"TNM: {t.raw_stage}")

            for bm in report.entities.biomarkers:
                status_label = str(bm.status)
                if bm.percentage is not None:
                    status_label += f" ({bm.percentage}%)"
                elif bm.ihc_score:
                    status_label += f" (IHC {bm.ihc_score})"
                biomarkers[bm.name] = status_label
                findings.append(f"{bm.name}: {status_label}")

            for td in report.entities.tumor_dimensions:
                dim_str = f"{td.primary_size_mm} mm" if td.primary_size_mm else "measured"
                findings.append(f"Tumor Size: {dim_str}")

            for ln in report.entities.lymph_nodes:
                if ln.nodes_examined is not None and ln.nodes_positive is not None:
                    ln_str = f"{ln.nodes_positive}/{ln.nodes_examined} positive"
                else:
                    ln_str = ln.span.snippet
                findings.append(f"Lymph Nodes: {ln_str}")

            entry = MultiReportTimelineEntry(
                report_id=report.report_id,
                date_str=report.chronological_date,
                modality=report.modality,
                key_findings=findings,
                birads_category=birads_val,
                tnm_stage=tnm_val,
                biomarkers=biomarkers,
            )
            timeline.append(entry)

        return timeline

    def evaluate_concordance(self) -> tuple[ConcordanceStatus, list[str]]:
        """Evaluate radiologic-pathologic concordance between imaging and biopsy reports.

        Follows ACR and ASCO/CAP radiologic-pathologic correlation guidelines:
        - BI-RADS 4C or 5 lesions on imaging require explanatory malignant or high-risk histology.
        - If high suspicion imaging yields completely benign pathology without explanatory lesion,
          it is flagged as DISCORDANT (prompting re-biopsy or multidisciplinary review).
        - If biopsy confirms malignancy or expected pathology, it is flagged as CONCORDANT.
        """
        imaging_reports = [
            r
            for r in self.context.reports
            if r.modality in {ReportModality.MAMMOGRAPHY, ReportModality.ULTRASOUND, ReportModality.MRI}
        ]
        pathology_reports = [r for r in self.context.reports if r.modality == ReportModality.PATHOLOGY]

        if not imaging_reports or not pathology_reports:
            return (
                ConcordanceStatus.NOT_APPLICABLE,
                ["Concordance assessment requires at least one imaging report and one pathology report."],
            )

        notes: list[str] = []

        # Extract highest imaging BI-RADS
        max_birads: str | None = None
        imaging_lateralities: set[str] = set()

        for imp in imaging_reports:
            for b in imp.entities.birads:
                val = b.category
                if not max_birads or val > max_birads:
                    max_birads = val
                if b.side and b.side != "unspecified":
                    imaging_lateralities.add(b.side.lower())

        # Extract pathology characteristics
        path_texts = " ".join(r.text.lower() for r in pathology_reports)
        has_malignancy = any(term in path_texts for term in _MALIGNANCY_HISTOLOGY_TERMS)
        has_benign = any(term in path_texts for term in _BENIGN_HISTOLOGY_TERMS)

        # Correlation logic
        if max_birads in {"4B", "4C", "5"}:
            if has_malignancy:
                status = ConcordanceStatus.CONCORDANT
                notes.append(
                    f"Concordant: High-suspicion imaging (BI-RADS {max_birads}) is histologically confirmed "
                    "by malignant/premalignant findings on pathology."
                )
            elif has_benign and not has_malignancy:
                status = ConcordanceStatus.DISCORDANT
                notes.append(
                    f"Discordance Alert: High-suspicion imaging (BI-RADS {max_birads}) yielded benign pathology. "
                    "Per clinical guidelines, repeat core biopsy or surgical excision should be reviewed."
                )
            else:
                status = ConcordanceStatus.INDETERMINATE
                notes.append(
                    f"Indeterminate: BI-RADS {max_birads} imaging requires definitive histological correlation."
                )
        elif max_birads in {"2", "3"}:
            if has_benign and not has_malignancy:
                status = ConcordanceStatus.CONCORDANT
                notes.append(
                    f"Concordant: Low-suspicion imaging (BI-RADS {max_birads}) correlates with benign histology."
                )
            elif has_malignancy:
                status = ConcordanceStatus.DISCORDANT
                notes.append(
                    f"Incidental Malignancy Discordance: BI-RADS {max_birads} imaging revealed unsuspected "
                    "malignancy on histological evaluation."
                )
            else:
                status = ConcordanceStatus.INDETERMINATE
                notes.append("Indeterminate: Pathology findings require radiologic review.")
        else:
            status = ConcordanceStatus.CONCORDANT if has_malignancy or has_benign else ConcordanceStatus.INDETERMINATE
            notes.append("Imaging and pathology findings documented.")

        return status, notes

    def generate_summary(self) -> MultiReportSummary:
        """Generate a complete multi-report summary across the patient session."""
        concordance_status, concordance_notes = self.evaluate_concordance()
        timeline = self.build_timeline()
        modalities = list(dict.fromkeys(r.modality for r in self.get_chronological_reports()))
        aggregated_entities = self.aggregate_entities()

        return MultiReportSummary(
            session_id=self.context.session_id,
            total_reports=len(self.context.reports),
            modalities_present=modalities,
            timeline=timeline,
            concordance=concordance_status,
            concordance_notes=concordance_notes,
            aggregated_entities=aggregated_entities,
        )
