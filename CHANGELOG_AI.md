# CHANGELOG_AI.md — AI Development Log

All notable changes, architectural updates, and feature implementations driven by AI pair-programming are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2026-08-26

### Added (Phase 3 — Entity Extraction Completed)

#### New Modules: Clinical Entity Parsers & Extraction Engine (`src/extraction/`)
- Created `src/extraction/birads_parser.py`:
  - `parse_birads(text: str) -> list[BiradsEntity]`: deterministic extraction of BI-RADS categories (0, 1, 2, 3, 4, 4A, 4B, 4C, 5, 6), category descriptors, breast side (`left`, `right`, `bilateral`, `unspecified`), and character source spans.
- Created `src/extraction/tnm_parser.py`:
  - `parse_tnm_staging(text: str) -> list[TnmEntity]`: deterministic extraction of pathological (`pT`, `pN`, `pM`) and clinical (`cT`, `cN`, `cM`) TNM staging strings (e.g., `pT1c N0 M0`, `pTis`), flag for pathological vs clinical, and character spans.
- Created `src/extraction/biomarker_parser.py`:
  - `parse_biomarkers(text: str) -> list[BiomarkerEntity]`: deterministic extraction of Estrogen Receptor (ER), Progesterone Receptor (PR), HER2/neu (IHC score, FISH status), and Ki-67 proliferation index (%), status (`positive`, `negative`, `equivocal`), staining intensity (`strong`, `moderate`, `weak`), and character spans.
- Created `src/extraction/tumor_parser.py`:
  - `parse_tumor_dimensions(text: str) -> list[TumorDimensionEntity]`: deterministic extraction of lesion size in mm and cm (1D, 2D, 3D measurements e.g. `1.6 x 1.4 x 1.5 cm`), quadrant (`upper outer quadrant`), clock position (`10 o'clock`), and character spans.
- Created `src/extraction/lymph_parser.py`:
  - `parse_lymph_nodes(text: str) -> list[LymphNodeEntity]`: deterministic extraction of lymph node counts examined vs positive (e.g. `2/5 nodes positive`), sentinel status flag, extranodal extension flag, and character spans.
- Created `src/extraction/engine.py`:
  - `extract_entities(text: str) -> ExtractedEntities`: orchestrator combining all 5 entity parsers into a single unified extraction interface.

#### Schema Updates (`src/api/schemas.py`)
- Defined entity Pydantic v2 schemas: `SourceSpan`, `BiradsEntity`, `TnmEntity`, `BiomarkerEntity`, `TumorDimensionEntity`, `LymphNodeEntity`, and container `ExtractedEntities`.
- Attached optional `entities: ExtractedEntities | None` field to `ReportResult`.

#### Pipeline Integration (`src/ingestion/pipeline.py`)
- Integrated Step 5 into `process_report`: calls `extract_entities(cleaned_text)` and attaches extracted entities to the returned `ReportResult`.

#### Dependencies & Architecture
- Added `langchain>=0.3.0`, `langgraph>=0.2.0`, and `langchain-community>=0.3.0` to `pyproject.toml` in preparation for Phase 5 (RAG) and Phase 7 (Conversational Agent).
- Updated `mypy` overrides for `langchain.*` and `langgraph.*`.

#### Test Suite
- Added `tests/test_extraction.py` with 13 comprehensive unit and integration tests verifying all 5 entity parsers, character span exactness (`raw_text[start:end] == snippet`), and full pipeline ingestion.
- **Total test count: 68 passing tests across 8 test modules (100% pass rate).**

---

## [0.2.0] - 2026-08-26

### Added (Phase 2 — OCR & Report Parser Completed)

#### New Module: OCR Engine
- Created `src/ingestion/ocr_engine.py` with:
  - `OcrResult` frozen dataclass: `text: str`, `confidence: float`, `page_count: int`.
  - `perform_ocr(content: bytes) -> OcrResult`: renders each PDF page to a PNG pixmap via PyMuPDF at 150 DPI, feeds it through `pytesseract.image_to_string()`, and computes mean word-level confidence from `image_to_data()`.
  - `_ocr_page()` private helper encapsulating per-page rendering and pytesseract calls.
  - `OcrUnavailableError` (503) raised if `pytesseract.TesseractNotFoundError` is caught — enables graceful degradation.
  - Low-confidence threshold defined at 0.5 (50%).

#### New Exception
- Added `OcrUnavailableError(AviothicError)` to `src/core/exceptions.py` (HTTP 503, error code `OCR_UNAVAILABLE`).

#### Schema Update
- Added `ocr_warning: str | None = None` optional field to `ReportResult` in `src/api/schemas.py`.

#### Pipeline Integration (`src/ingestion/pipeline.py`)
- When `extraction_result.is_scanned_likely` is `True`, calls `perform_ocr()`.
- On OCR success: uses OCR text as `source_text` for cleaning; maps float confidence → `high`/`medium`/`low` literal tier for `ReportConfidence.text_extraction`.
- On OCR confidence < 50%: sets `ocr_warning` with explicit percentage and advice to review manually.
- On `OcrUnavailableError`: sets `ocr_warning` describing missing Tesseract binary; degrades gracefully without crashing.

#### Dependencies
- Added `pytesseract>=0.3.13,<0.4` and `pillow>=10.0,<13.0` to `[project.dependencies]` in `pyproject.toml`.
- Added `pytesseract.*` to `[[tool.mypy.overrides]]` ignore list.

#### Test Suite
- Added `tests/test_ocr_engine.py` (5 tests, all mocking `pytesseract` — no Tesseract binary required in CI):
  - `test_perform_ocr_returns_ocr_result` — verifies `OcrResult` field types.
  - `test_perform_ocr_high_confidence` — mean confidence ≥ 0.75 for high word scores.
  - `test_perform_ocr_low_confidence` — confidence < 0.5 for low word scores.
  - `test_perform_ocr_raises_ocr_unavailable_when_tesseract_missing` — `OcrUnavailableError` on `TesseractNotFoundError`.
  - `test_perform_ocr_empty_confidence_list` — confidence = 0.0 when no valid words detected.
- **Total test count: 55 tests passing (100% pass rate).**



---

## [0.1.0] - 2026-08-26

### Added (Phase 1 — Data Ingestion & Preprocessing Completed)

#### Core Engine & Configuration
- Created `src/core/config.py` using `pydantic-settings` to manage environment variables (`AVIOTHIC_API_KEY`, file size limits, environment flags).
- Implemented structured JSON/console logging system in `src/core/logging.py` using `structlog`.
- Created custom domain exception hierarchy in `src/core/exceptions.py` (`IngestionError`, `ValidationError`, `PDFExtractionError`, `AuthenticationError`).
- Built API Key authentication middleware in `src/api/middleware.py` enforcing `X-API-Key` headers across endpoints (exempting `/health` and `/docs`).

#### Ingestion & Preprocessing Pipeline
- **File Validation** (`src/ingestion/validator.py`): Added file size checking (default max 10MB) and MIME-type validation for PDF documents.
- **PDF Extraction** (`src/ingestion/pdf_extractor.py`): Implemented native text extraction using PyMuPDF (`fitz`) with error handling for corrupted/empty PDFs.
- **Text Cleaning** (`src/ingestion/text_cleaner.py`): Built text cleaning pipeline for stripping null bytes, normalizing whitespace, removing headers/footers, and standardizing unicode characters.
- **Report Classification** (`src/ingestion/report_classifier.py`): Developed regex and keyword classifier supporting `mammography`, `ultrasound`, `mri`, `pet_ct`, `pathology`, and `discharge_summary` report types.
- **Date Extraction** (`src/ingestion/date_extractor.py`): Implemented extraction of report/examination dates using ISO, US, and clinical narrative text patterns.
- **Pipeline Orchestrator** (`src/ingestion/pipeline.py`): Integrated validation, extraction, cleaning, classification, and date parsing into a unified pipeline function returning structured JSON representations.

#### API Endpoints & Application Structure
- Created FastAPI app instance in `src/api/app.py` and `src/main.py`.
- Built POST `/api/v1/upload` endpoint for PDF ingestion in `src/api/routers/upload.py`.
- Built GET `/health` status endpoint and added root redirect to `/docs` in `src/api/routers/health.py`.
- Defined request and response models in `src/api/schemas.py`.

#### Automated Testing Suite
- Created test fixtures and unit/integration tests in `tests/`:
  - `tests/test_date_extractor.py` (10 tests)
  - `tests/test_health.py` (5 tests)
  - `tests/test_pdf_extractor.py` (4 tests)
  - `tests/test_report_classifier.py` (9 tests)
  - `tests/test_text_cleaner.py` (11 tests)
  - `tests/test_upload.py` (11 tests)
- Total test count: **50 tests passing (100% pass rate)**.

#### Infrastructure & Dependencies
- Configured project environment in `pyproject.toml` with pinned dependencies (`fastapi`, `uvicorn`, `pymupdf`, `pydantic`, `structlog`, `pytest`).
- Added `Dockerfile` and `docker-compose.yml` for containerized application execution.

---

### Recent Commits

- `63eb9a1` — `feat: add root path redirect to /docs and update auth exemptions`
- `066b927` — `chore: clean up tracked files and update .gitignore`
- `8464ae8` — `feat: complete phase 1 data ingestion and preprocessing pipeline`
