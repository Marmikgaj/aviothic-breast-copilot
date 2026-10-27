"""Shared pytest fixtures for the Aviothic test suite.

All fixtures use synthetic/mock data — no real patient data (Rules.md §2).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Set test API key before importing application code.
os.environ["AVIOTHIC_API_KEY"] = "test-api-key-for-testing"
os.environ["AVIOTHIC_ENV"] = "development"
os.environ["AVIOTHIC_LOG_LEVEL"] = "DEBUG"
os.environ["AVIOTHIC_UPLOAD_DIR"] = "./test_uploads"

from src.api.app import create_app  # noqa: E402
from src.api.routers.upload import get_job_store  # noqa: E402

# The test API key used in all authenticated requests.
TEST_API_KEY = "test-api-key-for-testing"


@pytest.fixture()
def app() -> FastAPI:
    """Create a fresh FastAPI application for each test."""
    application = create_app()
    return application


@pytest.fixture()
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client wired to the test application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """Return headers with a valid API key."""
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture(autouse=True)
def _clear_job_store() -> Iterator[None]:
    """Clear the in-memory job store before each test."""
    store = get_job_store()
    store.clear()
    yield
    store.clear()


@pytest.fixture()
def sample_mammography_pdf() -> bytes:
    """Generate a synthetic mammography report PDF.

    Uses fpdf2 to create a minimal text-native PDF with realistic
    mammography report content. No real patient data (Rules.md §2).
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    content = """BREAST IMAGING REPORT

Patient: Jane Doe (SYNTHETIC - NOT A REAL PATIENT)
MRN: SYNTH-000001
Date of Exam: 01/15/2026
Referring Physician: Dr. Smith

EXAMINATION: Bilateral Diagnostic Mammography

CLINICAL HISTORY:
52-year-old female presenting for annual screening mammography.
No palpable abnormalities. No prior history of breast cancer.

TECHNIQUE:
Bilateral craniocaudal (CC) and mediolateral oblique (MLO) views
were obtained using digital mammography with tomosynthesis.

BREAST DENSITY:
The breasts are heterogeneously dense, which may obscure small masses.
ACR Breast Density Category: C

FINDINGS:
RIGHT BREAST: No suspicious masses, calcifications, or architectural
distortion identified. No skin thickening or axillary lymphadenopathy.

LEFT BREAST: A 6mm group of amorphous calcifications is identified
in the upper outer quadrant at approximately 2 o'clock position,
8 cm from the nipple. No associated mass or architectural distortion.

No suspicious axillary lymphadenopathy bilaterally.

ASSESSMENT:
BI-RADS Category 4A - Low Suspicion for Malignancy

RECOMMENDATION:
Tissue diagnosis recommended. Stereotactic-guided biopsy of the
left breast calcifications is suggested.

Electronically signed by:
Dr. Sarah Chen, M.D.
Board Certified Radiologist
Date: 01/15/2026
"""

    for line in content.strip().split("\n"):
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


@pytest.fixture()
def sample_pathology_pdf() -> bytes:
    """Generate a synthetic pathology report PDF."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    content = """SURGICAL PATHOLOGY REPORT

Patient: Jane Doe (SYNTHETIC - NOT A REAL PATIENT)
MRN: SYNTH-000001
Date of Procedure: 02/01/2026
Pathologist: Dr. James Okonkwo

SPECIMEN: Left breast, stereotactic core biopsy

CLINICAL HISTORY:
Amorphous calcifications in left breast upper outer quadrant.
BI-RADS 4A.

GROSS DESCRIPTION:
Received in formalin labeled "left breast biopsy" are multiple
tan-white tissue cores measuring 1.0-1.5 cm in length.

MICROSCOPIC DESCRIPTION:
Sections show breast tissue with foci of ductal carcinoma in situ
(DCIS), cribriform and solid patterns. Nuclear grade 2 (intermediate).
No definite invasive carcinoma identified. Calcifications are
present within the DCIS foci.

IMMUNOHISTOCHEMISTRY:
ER: Positive (95% of tumor nuclei, strong intensity)
PR: Positive (80% of tumor nuclei, moderate intensity)
HER2: Negative (score 1+)
Ki-67: 12% (low proliferative index)

TNM STAGING (pathological):
pTis (DCIS) - No invasive component

DIAGNOSIS:
LEFT BREAST, STEREOTACTIC CORE BIOPSY:
- Ductal carcinoma in situ (DCIS), intermediate nuclear grade
- ER positive, PR positive, HER2 negative
- Ki-67: 12%
- No invasive carcinoma identified

Report Date: 02/05/2026
"""

    for line in content.strip().split("\n"):
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


@pytest.fixture()
def sample_plain_text_content() -> str:
    """Realistic mammography report text for unit-testing extraction/classification."""
    return """BREAST IMAGING REPORT

Patient: Jane Doe (SYNTHETIC)
Date of Exam: 03/20/2026

EXAMINATION: Bilateral Screening Mammography

TECHNIQUE: Digital mammography with tomosynthesis.

BREAST DENSITY: Heterogeneously dense (Category C).

FINDINGS:
RIGHT BREAST: No suspicious masses, calcifications, or architectural distortion.
LEFT BREAST: Stable benign-appearing calcifications in the lower inner quadrant.

ASSESSMENT: BI-RADS 2 - Benign

RECOMMENDATION: Routine annual screening mammography in 12 months.

Signed: Dr. Sarah Chen, M.D.
Date: 03/20/2026
"""
