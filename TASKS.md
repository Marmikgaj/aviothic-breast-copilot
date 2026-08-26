# TASKS.md — Project Task Tracker & Roadmap

This file tracks the implementation status of all tasks across the 8 development phases of the **Aviothic Breast Cancer Report Copilot**.

---

## Overall Progress Summary

- [x] **Phase 1 — Data Ingestion & Preprocessing** (100% Complete)
- [x] **Phase 2 — OCR & Report Parser** (100% Complete)
- [x] **Phase 3 — Entity Extraction** (100% Complete)
- [ ] **Phase 4 — Fine-Tune Oncology LLM** (0% Complete)
- [ ] **Phase 5 — Build RAG Engine** (0% Complete)
- [ ] **Phase 6 — Build Patient Context Memory** (0% Complete)
- [ ] **Phase 7 — Conversational Assistant** (0% Complete)
- [ ] **Phase 8 — Evaluation & Deployment** (0% Complete)

---

## Detailed Task Breakdown

### Phase 1 — Data Ingestion & Preprocessing `[COMPLETED]`

**Goal:** Establish end-to-end ingestion of native PDF reports, file validation, text cleaning, classification, date extraction, and REST API endpoints.

- [x] **Core Infrastructure & Configuration**
  - [x] Configure Pydantic Settings (`src/core/config.py`)
  - [x] Setup `structlog` structured logging (`src/core/logging.py`)
  - [x] Define custom domain exceptions (`src/core/exceptions.py`)
  - [x] Add API Key authentication middleware (`src/api/middleware.py`)
- [x] **Ingestion Components**
  - [x] Implement upload file validation (`src/ingestion/validator.py`)
  - [x] Implement PyMuPDF native PDF text extractor (`src/ingestion/pdf_extractor.py`)
  - [x] Build medical text cleaner & normalizer (`src/ingestion/text_cleaner.py`)
  - [x] Build report modality classifier (`src/ingestion/report_classifier.py`)
  - [x] Build clinical report date extractor (`src/ingestion/date_extractor.py`)
  - [x] Orchestrate full ingestion pipeline (`src/ingestion/pipeline.py`)
- [x] **API & Endpoints**
  - [x] Create POST `/api/v1/upload` endpoint (`src/api/routers/upload.py`)
  - [x] Create GET `/health` endpoint and root docs redirect (`src/api/routers/health.py`, `src/main.py`)
  - [x] Define OpenAPI & Pydantic response models (`src/api/schemas.py`)
- [x] **Testing & Verification**
  - [x] Test date extractor pattern matching (`tests/test_date_extractor.py`)
  - [x] Test report classification logic (`tests/test_report_classifier.py`)
  - [x] Test text cleaning rules (`tests/test_text_cleaner.py`)
  - [x] Test PDF extraction handling (`tests/test_pdf_extractor.py`)
  - [x] Test upload API routes and auth middleware (`tests/test_upload.py`)
  - [x] Verify all 50 unit and integration tests pass cleanly

---

### Phase 2 — OCR & Report Parser `[COMPLETED]`

**Goal:** Robust extraction from scanned/image-based reports, including tables, with confidence scoring.

- [x] **OCR Engine Integration**
  - [x] Implement Tesseract OCR fallback via `pytesseract` (`src/ingestion/ocr_engine.py`)
  - [x] Render PDF pages to images using PyMuPDF pixmaps for non-text PDFs
  - [x] Add `pytesseract>=0.3.13` and `pillow>=10.0` to `pyproject.toml` deps
- [x] **Confidence Scoring & Graceful Degradation**
  - [x] Compute mean word-level confidence score from `image_to_data()` output
  - [x] Map float confidence → `high` / `medium` / `low` tier in pipeline
  - [x] Raise `OcrUnavailableError` (503) when Tesseract binary not found
  - [x] Set `ocr_warning` on `ReportResult` for low-confidence (< 50%) or unavailable OCR
  - [x] Add `ocr_warning: str | None` field to `ReportResult` schema
- [x] **Testing & Validation**
  - [x] Add `tests/test_ocr_engine.py` with 5 unit tests (all mocking pytesseract)
  - [x] Verify all 55 tests pass (50 Phase 1 + 5 Phase 2)

---

### Phase 3 — Entity Extraction `[COMPLETED]`

**Goal:** Extraction of BI-RADS, TNM staging, tumor size, biomarkers, and lymph node status across report formats.

- [x] **NER Framework & Rule Engine**
  - [x] Initialize spaCy / RegEx medical extraction pipeline
  - [x] Build BI-RADS parser (Categories 0–6, side, descriptor) (`src/extraction/birads_parser.py`)
  - [x] Build TNM staging extractor (pT0–pT4, pN0–pN3, pM0–pM1, cTNM, DCIS) (`src/extraction/tnm_parser.py`)
  - [x] Build tumor dimension & size extractor (1D/2D/3D mm/cm, quadrant, clock position) (`src/extraction/tumor_parser.py`)
  - [x] Build biomarker extractor (ER, PR, HER2 IHC/FISH, Ki-67 %) (`src/extraction/biomarker_parser.py`)
  - [x] Build lymph node status parser (nodes examined/positive, sentinel status) (`src/extraction/lymph_parser.py`)
  - [x] Build entity engine orchestrator (`src/extraction/engine.py`)
- [x] **Span Tracking & Validation**
  - [x] Track exact character source spans (`start_char`, `end_char`, `snippet`) for all extracted entities
  - [x] Add Pydantic v2 schemas for entity models to `src/api/schemas.py`
  - [x] Add automated unit & integration tests with span validation in `tests/test_extraction.py`
  - [x] Verify all 68 tests pass across 8 test suites

---

### Phase 4 — Fine-Tune Oncology LLM `[PLANNED]`

**Goal:** Fine-tune Qwen3-8B / Llama3-8B for clinical explanation and reasoning without hallucination.

- [ ] **Dataset Preparation**
  - [ ] Collect & de-identify synthetic/public oncology instruction data
  - [ ] Format prompt-response pairs for single-turn reasoning
- [ ] **Fine-Tuning Execution**
  - [ ] Set up Unsloth + PEFT QLoRA pipeline
  - [ ] Track training metrics in Weights & Biases
  - [ ] Benchmark hallucination rate on held-out evaluation prompts

---

### Phase 5 — Build RAG Engine `[PLANNED]`

**Goal:** Retrieval-augmented generation grounded in PubMed abstracts and NCCN/ASCO clinical guidelines.

- [ ] **Vector Store & Embeddings**
  - [ ] Set up embedded ChromaDB instance
  - [ ] Configure `bge-large-en` / `BioClinicalBERT` embedding pipeline
  - [ ] Index PubMed Central open-access abstracts & cleared guidelines
- [ ] **Retrieval & Citation**
  - [ ] Implement query vectorizer and top-k passage retriever
  - [ ] Build citation formatting engine (linking claims to source IDs)

---

### Phase 6 — Build Patient Context Memory `[PLANNED]`

**Goal:** Session-scoped context memory managing multiple reports for a single patient session.

- [ ] **Context Management**
  - [ ] Implement `PatientContext` session container
  - [ ] Build multi-report aggregator
  - [ ] Design context window truncation & summarization logic

---

### Phase 7 — Conversational Assistant `[PLANNED]`

**Goal:** Grounded chat assistant supporting multi-turn Q&A, report comparison, and patient-friendly summaries.

- [ ] **Chat API & Guardrails**
  - [ ] Build `/api/v1/sessions/{id}/chat` endpoint
  - [ ] Integrate vLLM inference backend
  - [ ] Wire safety & citation layer into response pipeline
  - [ ] Generate plain-language patient summaries with mandatory disclaimers

---

### Phase 8 — Evaluation & Deployment `[PLANNED]`

**Goal:** Production packaging, performance evaluation, and containerized deployment.

- [ ] **Benchmark & Metrics Evaluation**
  - [ ] Evaluate extraction precision/recall (target ≥ 0.85)
  - [ ] Evaluate hallucination rate (target < 5%)
  - [ ] Measure p95 latency (< 30s ingestion, < 5s chat turn)
- [ ] **Deployment Packaging**
  - [ ] Finalize production Dockerfile & compose setup
  - [ ] Deploy to GPU instance (RunPod / Vast.ai)
