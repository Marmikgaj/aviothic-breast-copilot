"""Tests for the keyword-based report type classifier."""

from __future__ import annotations

import pytest

from src.ingestion.report_classifier import detect_report_type


class TestReportClassifier:
    """Report type classifier test suite."""

    def test_mammography_detection_high_confidence(self) -> None:
        """Text with strong mammography keywords should be classified with high confidence."""
        text = """
        BILATERAL SCREENING MAMMOGRAPHY
        Tomosynthesis was performed.
        Breast density: heterogeneously dense.
        BI-RADS Category 2 - Benign.
        Craniocaudal and mediolateral oblique views obtained.
        No suspicious calcifications identified.
        """
        modality, confidence = detect_report_type(text)
        assert modality == "mammography"
        assert confidence == "high"

    def test_pathology_detection_high_confidence(self) -> None:
        """Text with strong pathology keywords should be classified with high confidence."""
        text = """
        SURGICAL PATHOLOGY REPORT
        Specimen: Left breast core biopsy
        Histology: Invasive ductal carcinoma
        ER/PR: Positive
        HER2: Negative (score 1+)
        Ki-67: 15%
        Immunohistochemistry performed.
        Tumor grade 2.
        """
        modality, confidence = detect_report_type(text)
        assert modality == "pathology"
        assert confidence == "high"

    def test_ultrasound_detection(self) -> None:
        """Ultrasound-specific terminology should be detected."""
        text = """
        BREAST ULTRASOUND REPORT
        A hypoechoic lesion measuring 8mm is identified.
        Doppler flow assessment shows no increased vascularity.
        The lesion appears cystic with anechoic center.
        """
        modality, confidence = detect_report_type(text)
        assert modality == "ultrasound"
        assert confidence in ("high", "medium")

    def test_mri_detection(self) -> None:
        """MRI-specific terminology should be detected."""
        text = """
        BREAST MRI WITH CONTRAST
        Dynamic contrast-enhanced sequences obtained.
        Kinetic curve analysis performed.
        T2 weighted images show no abnormality.
        Gadolinium administered. Diffusion weighted imaging normal.
        """
        modality, confidence = detect_report_type(text)
        assert modality == "mri"
        assert confidence in ("high", "medium")

    def test_pet_ct_detection(self) -> None:
        """PET-CT-specific terminology should be detected."""
        text = """
        PET/CT EXAMINATION
        FDG tracer administered.
        SUVmax of 4.5 in left breast lesion.
        Metabolic activity noted. Standardized uptake values recorded.
        """
        modality, confidence = detect_report_type(text)
        assert modality == "pet_ct"
        assert confidence in ("high", "medium")

    def test_discharge_detection(self) -> None:
        """Discharge summary keywords should be detected."""
        text = """
        DISCHARGE SUMMARY
        Admission Date: 01/10/2026
        Discharge Date: 01/15/2026
        Hospital Course: Patient underwent left mastectomy.
        Discharge Diagnosis: Breast cancer, stage IIA.
        Discharge Medications: Tamoxifen 20mg daily.
        Disposition: Home with follow-up in 2 weeks.
        """
        modality, confidence = detect_report_type(text)
        assert modality == "discharge"
        assert confidence in ("high", "medium")

    def test_empty_text_returns_none(self) -> None:
        """Empty text should return None with low confidence."""
        modality, confidence = detect_report_type("")
        assert modality is None
        assert confidence == "low"

    def test_ambiguous_text_returns_low_confidence(self) -> None:
        """Generic text without modality-specific terms should be low confidence."""
        text = "The patient is a 55-year-old female with a history of breast cancer."
        modality, confidence = detect_report_type(text)
        # Might or might not detect something, but confidence should not be high.
        if modality is not None:
            assert confidence in ("low", "medium")

    def test_mammography_from_fixture(self, sample_plain_text_content: str) -> None:
        """The shared mammography fixture should be classified correctly."""
        modality, confidence = detect_report_type(sample_plain_text_content)
        assert modality == "mammography"
        assert confidence in ("high", "medium")
