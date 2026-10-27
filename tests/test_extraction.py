"""Tests for Phase 3 clinical entity extraction engine and parsers.

All tests use synthetic medical text data — no real patient data (Rules.md §2).
Includes source span validation: raw_text[start:end] == snippet for 100% auditability.
"""

from __future__ import annotations

import pytest

from src.extraction.biomarker_parser import parse_biomarkers
from src.extraction.birads_parser import parse_birads
from src.extraction.lymph_parser import parse_lymph_nodes
from src.extraction.tnm_parser import parse_tnm_staging
from src.extraction.tumor_parser import parse_tumor_dimensions
from src.ingestion.pipeline import process_report


class TestBiradsParser:
    """Test suite for BI-RADS assessment parser."""

    def test_parse_birads_4a(self) -> None:
        text = "ASSESSMENT: BI-RADS Category 4A - Low Suspicion for Malignancy"
        results = parse_birads(text)

        assert len(results) == 1
        b = results[0]
        assert b.category == "4A"
        assert b.descriptor == "Low Suspicion for Malignancy"
        assert "BI-RADS Category 4A" in b.span.snippet
        assert text[b.span.start_char : b.span.end_char] == b.span.snippet

    def test_parse_birads_with_left_side_context(self) -> None:
        text = "LEFT BREAST: BI-RADS 4C - High Suspicion for Malignancy."
        results = parse_birads(text)

        assert len(results) == 1
        b = results[0]
        assert b.category == "4C"
        assert b.side == "left"
        assert text[b.span.start_char : b.span.end_char] == b.span.snippet

    def test_parse_birads_category_5(self) -> None:
        text = "FINAL IMPRESSION: BIRADS Category 5"
        results = parse_birads(text)

        assert len(results) == 1
        assert results[0].category == "5"
        assert "Suggestive of Malignancy" in (results[0].descriptor or "")


class TestTnmParser:
    """Test suite for TNM staging parser."""

    def test_parse_pathological_tnm(self) -> None:
        text = "TNM STAGING (pathological): pT1c N0 M0"
        results = parse_tnm_staging(text)

        assert len(results) == 1
        t = results[0]
        assert t.t_stage == "pT1c"
        assert t.n_stage == "N0"
        assert t.m_stage == "M0"
        assert t.is_pathological is True
        assert text[t.span.start_char : t.span.end_char] == t.span.snippet

    def test_parse_dcis_tnm(self) -> None:
        text = "Pathological Stage: pTis N0 M0"
        results = parse_tnm_staging(text)

        assert len(results) == 1
        assert results[0].t_stage == "pTis"


class TestBiomarkerParser:
    """Test suite for ER, PR, HER2, Ki-67 biomarker parser."""

    def test_parse_er_pr_positive(self) -> None:
        text = (
            "IMMUNOHISTOCHEMISTRY:\n"
            "ER: Positive (90% of tumor nuclei, strong intensity)\n"
            "PR: Positive (70% of tumor nuclei, moderate intensity)"
        )
        results = parse_biomarkers(text)

        er = next(b for b in results if b.name == "ER")
        pr = next(b for b in results if b.name == "PR")

        assert er.status == "positive"
        assert er.percentage == 90.0
        assert er.intensity == "strong"
        assert text[er.span.start_char : er.span.end_char] == er.span.snippet

        assert pr.status == "positive"
        assert pr.percentage == 70.0
        assert pr.intensity == "moderate"

    def test_parse_her2_negative(self) -> None:
        text = "HER2: Negative (score 1+)"
        results = parse_biomarkers(text)

        her2 = next(b for b in results if b.name == "HER2")
        assert her2.status == "negative"
        assert her2.ihc_score == "1+"
        assert text[her2.span.start_char : her2.span.end_char] == her2.span.snippet

    def test_parse_ki67_index(self) -> None:
        text = "Ki-67: 18% (intermediate proliferative index)"
        results = parse_biomarkers(text)

        ki67 = next(b for b in results if b.name == "Ki-67")
        assert ki67.percentage == 18.0
        assert ki67.status == "positive"


class TestTumorParser:
    """Test suite for tumor size and location parser."""

    def test_parse_3d_dimensions(self) -> None:
        text = (
            "LEFT BREAST: In the upper outer quadrant at 10 o'clock position, "
            "there is a 1.6 x 1.4 x 1.5 cm irregular mass."
        )
        results = parse_tumor_dimensions(text)

        assert len(results) >= 1
        t = results[0]
        assert t.primary_size_mm == 16.0
        assert t.dimensions_mm == [16.0, 14.0, 15.0]
        assert t.location_quadrant == "upper outer quadrant"
        assert "10 o'clock" in (t.clock_position or "")
        assert text[t.span.start_char : t.span.end_char] == t.span.snippet

    def test_parse_single_dimension_mm(self) -> None:
        text = "A 8 mm mass identified in central quadrant"
        results = parse_tumor_dimensions(text)

        assert len(results) == 1
        assert results[0].primary_size_mm == 8.0


class TestLymphParser:
    """Test suite for lymph node status parser."""

    def test_parse_node_counts(self) -> None:
        text = "AXILLARY DISSECTION: 2/5 nodes positive for macrometastasis."
        results = parse_lymph_nodes(text)

        assert len(results) == 1
        node = results[0]
        assert node.nodes_examined == 5
        assert node.nodes_positive == 2
        assert text[node.span.start_char : node.span.end_char] == node.span.snippet


class TestPipelineExtractionIntegration:
    """Integration tests verifying full ingestion pipeline produces extracted entities."""

    @pytest.mark.asyncio
    async def test_mammography_pipeline_extracts_entities(self, sample_mammography_pdf: bytes) -> None:
        result = await process_report(report_id="test-rep-01", content=sample_mammography_pdf, filename="mammo.pdf")

        assert result.entities is not None
        assert len(result.entities.birads) >= 1
        assert result.entities.birads[0].category == "4A"

    @pytest.mark.asyncio
    async def test_pathology_pipeline_extracts_entities(self, sample_pathology_pdf: bytes) -> None:
        result = await process_report(report_id="test-rep-02", content=sample_pathology_pdf, filename="path.pdf")

        assert result.entities is not None
        assert len(result.entities.biomarkers) >= 2
        assert len(result.entities.tnm_staging) >= 1
