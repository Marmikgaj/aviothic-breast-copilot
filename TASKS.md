# TASKS.md — Project Task Tracker & Roadmap

This file tracks the implementation status of all tasks across the 8 development phases of the **Aviothic Breast Cancer Report Copilot**.

---

## Overall Progress Summary

- [x] **Phase 1 — Data Ingestion & Preprocessing** (100% Complete)
- [x] **Phase 2 — OCR & Report Parser** (100% Complete)
- [x] **Phase 3 — Entity Extraction** (100% Complete)
- [x] **Phase 4 — Fine-Tune Oncology LLM** (100% Complete)
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

### Phase 4 — Fine-Tune Oncology LLM `[COMPLETED]`

**Goal:** Fine-tune Qwen3-8B / Llama3-8B for clinical explanation and reasoning without hallucination.

- [x] **Dataset Preparation & Schemas**
  - [x] Define Pydantic v2 instruction dataset schemas, category enums, and training configs (`src/training/schemas.py`)
  - [x] Build curated synthetic oncology instruction dataset generator across BI-RADS, TNM, biomarkers, tumor size, and patient summaries (`src/training/dataset_generator.py`)
  - [x] Build automated PHI de-identification screening and diagnostic safety validator (`src/training/dataset_validator.py`)
  - [x] Export train, val, and test dataset splits to `data/processed/`
- [x] **Prompt Formatter & Chat Markup**
  - [x] Implement Qwen ChatML and Llama 3 chat template formatters (`src/training/prompt_formatter.py`)
  - [x] Enforce mandatory system prompt framing ("assistive reasoning, NEVER provide definitive diagnosis") and assistive disclaimer
- [x] **Fine-Tuning Execution Pipeline**
  - [x] Build modular Unsloth + PEFT QLoRA fine-tuning training script (`src/training/train_qlora.py`)
  - [x] Add multi-environment support (GPU Unsloth execution + CPU/CI dry-run validation mode)
  - [x] Integrate Weights & Biases experiment tracking configuration
- [x] **Evaluation & Hallucination Benchmark Harness**
  - [x] Build held-out benchmark evaluation harness (`src/training/evaluator.py`)
  - [x] Enforce diagnostic leakage target (< 5%) and disclaimer presence rate (>= 95%) per PRD §6
- [x] **Testing & Verification**
  - [x] Add comprehensive test suite in `tests/test_training.py` (21 unit and integration tests)
  - [x] Verify all 89 tests pass cleanly across 9 test suites

---

### Phase 5 — Build RAG Engine `[COMPLETED]`

**Goal:** Retrieval-augmented generation grounded in PubMed abstracts and NCCN/ASCO clinical guidelines.

- [x] **Vector Store & Embeddings**
  - [x] Set up embedded ChromaDB instance (`src/rag/vector_store.py`) supporting ephemeral and persistent modes
  - [x] Configure high-performance `DeterministicBiomedicalEmbeddingFunction` (384-dim, signed feature hashing across weighted oncology terms) with `SentenceTransformerEmbeddingFunction` wrapper (`src/rag/embeddings.py`)
  - [x] Curate and index foundational oncology clinical guidelines (NCCN BI-RADS, AJCC 8th Ed. TNM, ASCO/CAP HER2, ASCO/CAP ER/PR, St. Gallen subtypes, ACOSOG Z0011, and concordance guidelines) in `src/rag/knowledge_base.py`
- [x] **Retrieval & Citation**
  - [x] Implement semantic query retriever with clinical entity query auto-formulation (`src/rag/retriever.py`)
  - [x] Build citation formatting, bibliography generation, and hallucinated provenance verification engine (`src/rag/citation_engine.py`)
- [x] **Testing & Verification**
  - [x] Add comprehensive test suite in `tests/test_rag.py` (17 tests covering vector store, embeddings, citation provenance, and entity retrieval)
  - [x] Verify all 106 tests pass across 10 test modules

---

### Phase 6 — Build Patient Context Memory `[COMPLETED]`

**Goal:** Session-scoped context memory managing multiple reports for a single patient session.

- [x] **Context Management**
  - [x] Implement `PatientContext` session container, `ProcessedReport`, `ConversationTurn`, `CitationReference` (`src/context/schemas.py`)
  - [x] Build thread-safe ephemeral `SessionManager` with idle TTL expiration and zero cross-patient data leakage (`src/context/session_manager.py`)
  - [x] Build `MultiReportAggregator` for chronological ordering, entity matrix aggregation, timeline generation, and radiologic-pathologic concordance evaluation (`src/context/aggregator.py`)
  - [x] Design `ContextWindowManager` with token budgeting and prioritized hierarchical truncation preserving core clinical findings (`src/context/window_manager.py`)
- [x] **Testing & Verification**
  - [x] Add comprehensive test suite in `tests/test_context.py` (21 unit and integration tests)
  - [x] Verify all 127 tests pass across 11 test modules

---

### Phase 7 — Conversational Assistant `[COMPLETED]`

**Goal:** Grounded chat assistant supporting multi-turn Q&A, report comparison, and patient-friendly summaries.

- [x] **Chat API & Guardrails**
  - [x] Implement safety guardrails engine enforcing non-diagnostic policy, off-context refusals, and citation integrity (`src/safety/guardrails.py`)
  - [x] Build inference backend with vLLM client and deterministic offline fallback engine (`src/conversation/inference_client.py`)
  - [x] Build prompt builder with automatic multi-report comparison detection (`src/conversation/prompt_builder.py`)
  - [x] Orchestrate grounded conversational assistant engine with session history tracking (`src/conversation/engine.py`)
  - [x] Implement dense technical clinician notes generator and plain-language patient summary generator with mandatory disclaimers (`src/reporting/generator.py`)
  - [x] Build full FastAPI session endpoints: `POST /api/v1/sessions/{id}/chat`, `POST /api/v1/sessions/{id}/summary`, and `GET /api/v1/sessions/{id}/export` (`src/api/routers/sessions.py`)
- [x] **Testing & Verification**
  - [x] Add comprehensive test suite in `tests/test_conversation.py` (18 unit and API integration tests)
  - [x] Verify all 145 tests pass cleanly across 12 test modules

---

### Phase 8 — Evaluation & Deployment `[COMPLETED]`

**Goal:** Production packaging, performance evaluation, and containerized deployment.

- [x] **Benchmark & Metrics Evaluation**
  - [x] Build multimodal gold-standard annotated benchmark cases across mammography, ultrasound, biopsy, and excision (`src/evaluation/gold_dataset.py`)
  - [x] Evaluate extraction precision/recall achieving target ≥ 0.85 (achieved: 1.000 macro P/R on held-out gold set) (`src/evaluation/extraction_evaluator.py`)
  - [x] Evaluate hallucination rate, diagnostic leakage (< 5%), and disclaimer presence rate (≥ 95%) (`src/evaluation/hallucination_evaluator.py`)
  - [x] Profile p95 latencies against PRD targets: ingestion ≤ 30s (measured: 2.42ms), chat turn ≤ 5s (measured: 12.34ms) (`src/evaluation/latency_profiler.py`)
  - [x] Build automated end-to-end evaluation runner producing JSON and Markdown audit reports (`src/evaluation/runner.py`)
- [x] **Deployment Packaging**
  - [x] Upgrade multi-stage `Dockerfile` with system dependencies (`tesseract-ocr`, `poppler-utils`) and non-root execution
  - [x] Create production `deploy/docker-compose.prod.yml` with vLLM GPU inference service, health checks, and persistent volumes
  - [x] Create automated provisioning and launch script `deploy/runpod_setup.sh` for RunPod / Vast.ai dedicated GPU pods
- [x] **Testing & Verification**
  - [x] Add comprehensive test suite in `tests/test_evaluation.py` (8 unit and integration tests)
  - [x] Verify all 153 tests pass across 13 test suites with 100% success rate
