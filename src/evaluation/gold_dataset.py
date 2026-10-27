"""Gold-standard held-out annotated benchmark dataset for breast oncology report extraction evaluation.

Complies with PRD §6: Held-out annotated set for extraction precision and recall evaluation.
Contains synthetic, de-identified multimodal clinical report texts across mammography,
ultrasound, and pathology biopsy/excision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GoldEntityAnnotation:
    """Expected clinical entity in a gold benchmark case."""

    category: str  # "birads", "tnm_staging", "biomarkers", "tumor_dimensions", "lymph_nodes"
    expected_value: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoldBenchmarkCase:
    """A single held-out report case with expert annotations."""

    case_id: str
    modality: str
    text: str
    expected_entities: list[GoldEntityAnnotation]


GOLD_BENCHMARK_CASES: list[GoldBenchmarkCase] = [
    GoldBenchmarkCase(
        case_id="gold_mammo_001",
        modality="mammography",
        text=(
            "DIAGNOSTIC BILATERAL MAMMOGRAM WITH TOMOSYNTHESIS\n"
            "History: 54-year-old female presenting with palpable mass in right breast.\n"
            "Findings: Dense fibroglandular parenchyma (Density C). In the right breast upper outer quadrant at "
            "10:00 position, 4 cm from the nipple, there is a newly identified irregular, spiculated hyperdense mass "
            "measuring 18 mm in maximum dimension. Associated fine pleomorphic microcalcifications are noted within "
            "the mass. Left breast is clear with no suspicious masses or architectural distortion.\n"
            "IMPRESSION: 18 mm spiculated right breast mass with suspicious calcifications.\n"
            "BI-RADS Category 4C: High suspicion for malignancy. Image-guided core biopsy is strongly recommended."
        ),
        expected_entities=[
            GoldEntityAnnotation(
                category="birads",
                expected_value="4C",
                attributes={"side": "right", "descriptor": "High suspicion for malignancy"},
            ),
            GoldEntityAnnotation(
                category="tumor_dimensions",
                expected_value="18.0",
                attributes={"primary_size_mm": 18.0},
            ),
        ],
    ),
    GoldBenchmarkCase(
        case_id="gold_path_002",
        modality="pathology",
        text=(
            "SURGICAL PATHOLOGY REPORT — CORE NEEDLE BIOPSY\n"
            "Specimen: Right breast 10:00 core biopsy.\n"
            "DIAGNOSIS: Invasive ductal carcinoma (no special type), Nottingham histologic grade 2 (tubule 3, "
            "nuclear pleomorphism 2, mitoses 1; total score 6/9). Associated intermediate-grade cribriform DCIS.\n"
            "Provisional Pathologic Stage: pT1c.\n"
            "BIOMARKER PROFILE (IHC):\n"
            "• Estrogen Receptor (ER): Positive, 95% strong nuclear staining.\n"
            "• Progesterone Receptor (PR): Positive, 80% moderate-to-strong nuclear staining.\n"
            "• HER2/neu: Negative (Score 1+, faint incomplete membrane staining in >10% of tumor cells).\n"
            "• Ki-67 Proliferation Index: 15% nuclear positivity."
        ),
        expected_entities=[
            GoldEntityAnnotation(
                category="tnm_staging",
                expected_value="pT1c",
                attributes={"is_pathological": True},
            ),
            GoldEntityAnnotation(
                category="biomarkers",
                expected_value="ER",
                attributes={"status": "positive", "percentage": 95.0},
            ),
            GoldEntityAnnotation(
                category="biomarkers",
                expected_value="PR",
                attributes={"status": "positive", "percentage": 80.0},
            ),
            GoldEntityAnnotation(
                category="biomarkers",
                expected_value="HER2",
                attributes={"status": "negative", "ihc_score": "1+"},
            ),
            GoldEntityAnnotation(
                category="biomarkers",
                expected_value="Ki-67",
                attributes={"percentage": 15.0},
            ),
        ],
    ),
    GoldBenchmarkCase(
        case_id="gold_us_003",
        modality="ultrasound",
        text=(
            "TARGETED BREAST ULTRASOUND\n"
            "Clinical indication: Pain in left breast lower inner quadrant.\n"
            "Findings: Targeted sonography of the left breast at the 8 o'clock position reveals an anechoic, "
            "well-circumscribed oval mass with posterior acoustic enhancement and thin walls, measuring 12 mm, "
            "characteristic of a simple benign cyst. No solid component, vascularity, or shadowing.\n"
            "IMPRESSION: Simple cyst, left breast.\n"
            "BI-RADS Category 2: Benign finding. Routine screening follow-up advised."
        ),
        expected_entities=[
            GoldEntityAnnotation(
                category="birads",
                expected_value="2",
                attributes={"side": "left"},
            ),
            GoldEntityAnnotation(
                category="tumor_dimensions",
                expected_value="12.0",
                attributes={"primary_size_mm": 12.0},
            ),
        ],
    ),
    GoldBenchmarkCase(
        case_id="gold_resection_004",
        modality="pathology",
        text=(
            "FINAL RESECTION PATHOLOGY REPORT\n"
            "Procedure: Right breast partial mastectomy (lumpectomy) with sentinel lymph node biopsy.\n"
            "Histologic Type: Invasive lobular carcinoma, classic variant, Grade 2.\n"
            "Tumor Dimensions: Greatest dimension of invasive focus is 24 mm.\n"
            "Surgical Margins: All margins uninvolved by invasive carcinoma or DCIS (closest margin 5 mm posterior).\n"
            "Lymph Node Status: Sentinel lymph node biopsy reveals 2 of 4 sentinel nodes positive for macrometastasis "
            "(largest metastasis 3.5 mm). Extranodal extension is absent.\n"
            "Pathological Staging: pT2 pN1a M0."
        ),
        expected_entities=[
            GoldEntityAnnotation(
                category="tnm_staging",
                expected_value="pT2",
                attributes={"is_pathological": True},
            ),
            GoldEntityAnnotation(
                category="tnm_staging",
                expected_value="pN1a",
                attributes={"is_pathological": True},
            ),
            GoldEntityAnnotation(
                category="tumor_dimensions",
                expected_value="24.0",
                attributes={"primary_size_mm": 24.0},
            ),
            GoldEntityAnnotation(
                category="lymph_nodes",
                expected_value="2/4",
                attributes={"nodes_examined": 4, "nodes_positive": 2},
            ),
        ],
    ),
]
