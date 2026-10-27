# CHANGELOG_AI.md — AI Development Log

All notable changes, architectural updates, and feature implementations driven by AI pair-programming are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-28

### Added (Phase 8 — Evaluation & Deployment Completed)

#### Benchmark, Metrics & Evaluation Harness
- Created `src/evaluation/schemas.py`:
  - `EntityMetric`: Structured precision, recall, and F1 tracker for individual entity categories.
  - `ExtractionEvaluationResult`: Aggregated macro metrics and PRD §6 threshold validation.
  - `HallucinationEvaluationResult`: Tracks citation presence rate, hallucination rate, and diagnostic leakage rate.
  - `LatencyBenchmarkResult`: Percentile latency profiler (mean, p50, p90, p95, max).
  - `FullSystemEvaluationReport`: Comprehensive system evaluation report schema.
- Created `src/evaluation/gold_dataset.py`:
  - Curated 4 expert-annotated gold-standard benchmark cases across mammography, ultrasound, needle biopsy, and lumpectomy resection (`GOLD_BENCHMARK_CASES`).
- Created `src/evaluation/extraction_evaluator.py`:
  - `evaluate_extraction()`: Evaluates rule-based extraction against gold standards, calculating precision, recall, and F1 across BI-RADS, TNM staging, biomarkers, tumor dimensions, and lymph nodes.
- Created `src/evaluation/hallucination_evaluator.py`:
  - `evaluate_hallucination_and_safety()`: Validates citation adherence, absence of unsupported clinical claims, zero diagnostic leakage (< 5% threshold), and mandatory disclaimer presence (≥ 95% threshold).
- Created `src/evaluation/latency_profiler.py`:
  - Measures p50/p90/p95 latency distributions for document ingestion/extraction and multi-turn conversational turns against PRD §6 targets (≤ 30s ingestion, ≤ 5s chat turns).
- Created `src/evaluation/runner.py`:
  - `run_full_system_evaluation()`: End-to-end evaluation runner producing `data/evaluation_report.json` and `data/evaluation_report.md`.
- Enhanced `src/extraction/tumor_parser.py`:
  - Added support for single tumor size phrases, "measuring" descriptors, and greatest dimension statements while strictly preventing span overlaps.

#### Production Deployment Packaging
- Created `deploy/docker-compose.prod.yml`:
  - Container orchestration with `aviothic_copilot_api` and `vllm` dedicated GPU model serving, health checks, resource limits, and persistent data volumes.
- Created `deploy/runpod_setup.sh`:
  - Automated deployment and provisioning script for RunPod / Vast.ai dedicated GPU pods (CUDA check, system packages, Tesseract OCR, uv environment, vLLM daemon, and production uvicorn launch).
- Upgraded `Dockerfile`:
  - Added `tesseract-ocr`, `tesseract-ocr-eng`, and `poppler-utils` in runtime stage for complete scanned PDF OCR capabilities.

#### Test Suite (`tests/test_evaluation.py`)
- Created `tests/test_evaluation.py` with 8 comprehensive unit and integration tests across 5 test classes (`TestGoldDataset`, `TestExtractionEvaluator`, `TestHallucinationEvaluator`, `TestLatencyProfiler`, `TestFullSystemRunner`).
- **Total test count: 153 passing tests across 13 test modules with 100% success rate.**

---

## [0.7.0] - 2026-10-28

### Added (Phase 7 — Conversational Assistant Completed)

#### New Modules: Conversational Assistant, Safety Guardrails & Reporting
- Created `src/safety/schemas.py`:
  - `SafetyCheckResult`: Pydantic model tracking safety compliance, diagnostic leakage, mandatory disclaimer adherence, citation verification, off-context flags, and sanitized response text.
- Created `src/safety/guardrails.py`:
  - `SafetyGuardrail`: Comprehensive clinical safety enforcement engine.
  - Strictly enforces Rules.md §8: NEVER state a definitive diagnosis or malignancy. Automatically intercepts and sanitizes diagnostic assertions with assistive framing.
  - Enforces mandatory assistive disclaimer presence (`MANDATORY_ASSISTIVE_DISCLAIMER`).
  - Verifies citation presence on clinical claims (BI-RADS, TNM staging, hormone receptors, chemotherapy, biopsy recommendations).
  - Out-of-domain / off-context query detection and standardized refusal (`OFF_CONTEXT_REFUSAL`).
  - De-identification and PHI leakage detection.
- Created `src/conversation/schemas.py`:
  - `ChatRequest`: Request schema with user message, streaming option, and maximum citations.
  - `ChatResponse`: Structured response schema with turn ID, session ID, answer, citations, concordance status, and latency.
- Created `src/conversation/inference_client.py`:
  - `BaseInferenceClient`: Abstract LLM inference interface.
  - `VLLMInferenceClient`: OpenAI-compatible HTTP client for production vLLM serving with timeout and fallback support.
  - `MockInferenceClient`: High-fidelity deterministic reasoning engine for offline development, CI, and test execution.
  - `get_inference_client()` factory with automatic fallback.
- Created `src/conversation/prompt_builder.py`:
  - `PromptBuilder`: Integrates system framing, token-budgeted patient context, and retrieved RAG guideline passages.
  - `is_comparison_query(query)`: Automated regex detection for cross-report comparison and concordance requests.
- Created `src/conversation/engine.py`:
  - `ConversationEngine`: End-to-end chat orchestration engine binding session memory, RAG retrieval, LLM inference, safety guardrails, citation formatting, and turn history updates.
- Created `src/reporting/schemas.py`:
  - `SummaryRequest`: Options for summary generation (audience, timeline).
  - `SummaryResponse`: Container for clinician-facing and patient-friendly summaries.
  - `SessionExport`: Complete structured JSON export schema for auditability and EHR integration.
- Created `src/reporting/generator.py`:
  - `SummaryGenerator`: Generates dense technical clinician notes for EHR pasting, plain-language patient guides for clinician review, and full structured JSON session exports.
- Created `src/api/routers/sessions.py`:
  - `POST /api/v1/sessions/{session_id}/chat`: Execute grounded conversational turn with RAG and citations.
  - `POST /api/v1/sessions/{session_id}/summary`: Generate dual clinician and patient summaries.
  - `GET /api/v1/sessions/{session_id}/export`: Export complete session data and audited findings as structured JSON.
  - Registered router in `src/api/app.py`.

#### Configuration Updates
- Added LLM inference settings to `src/core/config.py`: `llm_api_base`, `llm_model`, `llm_temperature`, `llm_max_new_tokens`, `llm_request_timeout`, `llm_mock_fallback`.

#### Test Suite (`tests/test_conversation.py`)
- Created `tests/test_conversation.py` with 18 unit and API integration tests across 5 test classes (`TestSafetyGuardrail`, `TestPromptBuilder`, `TestConversationEngine`, `TestSummaryGenerator`, `TestSessionsApiEndpoints`).
- **Total test count: 145 passing tests across 12 test modules (100% pass rate).**

---

## [0.6.0] - 2026-10-27

### Added (Phase 6 — Build Patient Context Memory Completed)

#### New Modules: Patient Context, Session Memory & Aggregation (`src/context/`)
- Created `src/context/schemas.py`:
  - `ConversationRole` (StrEnum): `USER`, `ASSISTANT`, `SYSTEM`.
  - `CitationSourceType` (StrEnum): `REPORT`, `GUIDELINE`, `PUBMED`.
  - `ReportModality` (StrEnum): `MAMMOGRAPHY`, `PATHOLOGY`, `ULTRASOUND`, `MRI`, `PET_CT`, `DISCHARGE_SUMMARY`, `UNKNOWN`.
  - `CitationReference`: Grounding reference model linking facts to report IDs or guidelines with source type, retrieval score, and text snippet.
  - `ConversationTurn`: Single conversation turn model with unique turn ID, role, content, citation list, and UTC timestamp.
  - `ProcessedReport`: Structured session report container with report ID, modality, clinical date, normalized text, and `ExtractedEntities`.
  - `ConcordanceStatus` (StrEnum): `CONCORDANT`, `DISCORDANT`, `INDETERMINATE`, `NOT_APPLICABLE`.
  - `MultiReportTimelineEntry`: Diagnostic trajectory timeline entry tracking findings, BI-RADS, TNM, and biomarker statuses chronologically.
  - `MultiReportSummary`: Unified multi-report synthesis across a session with modality list, timeline, concordance determination, and notes.
  - `PatientContext`: Ephemeral, session-scoped memory container managing reports, conversation history, and metadata.
  - `ContextBudget`: Context window token budgeting model with available context calculation.
- Created `src/context/session_manager.py`:
  - `SessionManager`: Thread-safe in-memory session manager with fine-grained read/write locking.
  - Automatic session cleanup after idle timeout (default 60 minutes) per ADR-002 and PRD §7.
  - Methods: `create_session()`, `get_session()`, `get_or_create_session()`, `add_report()`, `add_turn()`, `delete_session()`, `clear_expired_sessions()`, `active_session_count()`.
  - Zero cross-patient PHI persistence to disk.
- Created `src/context/aggregator.py`:
  - `MultiReportAggregator`: Cross-report synthesis engine for multi-report patient sessions.
  - Chronological timeline construction ordering examinations by date.
  - Cross-report entity matrix aggregation across imaging and pathology.
  - Radiologic-Pathologic Concordance Evaluation:
    - Flags high-suspicion imaging (BI-RADS 4C/5) confirmed by histology as `CONCORDANT`.
    - Detects false-negative biopsy discordance (BI-RADS 4C/5 with strictly benign tissue without explanatory lesion) as `DISCORDANT` with clinical follow-up alert.
    - Flags incidental findings or laterality discrepancies between imaging and pathology.
- Created `src/context/window_manager.py`:
  - `ContextWindowManager`: Token budgeting and hierarchical context truncation engine.
  - `estimate_tokens()`: Heuristic token estimator (4 chars/token).
  - Priority-based context assembly:
    - Priority 1 (Never dropped): Clinical query and structured clinical findings table (BI-RADS, TNM, biomarkers).
    - Priority 2: Retrieved guideline passages from RAG within token cap.
    - Priority 3: Recent conversation history via sliding window.
    - Priority 4: Report raw excerpts.
- Created `src/context/__init__.py`:
  - Public exports for all context schemas, aggregator, session manager, and window manager.

#### Test Suite (`tests/test_context.py`)
- Created `tests/test_context.py` with 21 unit and integration tests across 3 test classes (`TestSessionManager`, `TestMultiReportAggregator`, `TestContextWindowManager`).
- **Total test count: 127 passing tests across 11 test modules (100% pass rate).**

---

## [0.5.0] - 2026-10-27

### Added (Phase 5 — Build RAG Engine Completed)

#### New Modules: RAG Engine, Vector Store, Embeddings & Citation (`src/rag/`)
- Created `src/rag/schemas.py`:
  - `GuidelineSource` (StrEnum): `NCCN`, `ASCO_CAP`, `AJCC`, `ESMO`, `PUBMED`.
  - `GuidelineDocument`: Model for oncology guideline and literature documents with source, authors, year, citation label, PMID/DOI, keywords, and text.
  - `RetrievedPassage`: Model for retrieved passages with similarity score, rank, document provenance, and formatted citation.
  - `RetrievalQuery`: Query specification model with top-k, source filters, and similarity threshold.
  - `RetrievalResult`: Results container with query, ranked passages, formatted citations, latency, and context formatting helper `to_context_string()`.
- Created `src/rag/embeddings.py`:
  - `DeterministicBiomedicalEmbeddingFunction`: Fast, offline 384-dimensional dense embedding generator using dual-hash projections (MD5 + SHA-256) weighted by 50+ breast oncology anchor vocabulary terms and zero-drift signed character trigrams, L2 normalized.
  - `SentenceTransformerEmbeddingFunction`: Production wrapper for `sentence-transformers` models (e.g. `bge-large-en`, `BioClinicalBERT`) with automatic fallback to deterministic embeddings if missing.
  - Factory function `get_embedding_function()` with dependency detection.
- Created `src/rag/knowledge_base.py`:
  - Curated foundational breast oncology clinical guidelines:
    - NCCN Breast Cancer Screening and Diagnosis Guidelines (BI-RADS assessment, diagnostic workup).
    - AJCC Cancer Staging Manual (8th Edition) TNM staging criteria (T1-T4, pN0-pN3, M0-M1).
    - ASCO/CAP HER2 Testing Guidelines (IHC 0/1+/2+/3+, FISH reflex testing criteria).
    - ASCO/CAP ER/PR Receptor Testing Guidelines (1-100% positive, ER low positive 1-10%).
    - St. Gallen International Consensus (Luminal A, Luminal B, HER2-enriched, Triple-Negative subtypes).
    - ACOSOG Z0011 Sentinel Lymph Node Dissection Trial (JAMA 2017).
    - Image-guided Core Needle Biopsy Radiologic-Pathologic Concordance Guidelines (Radiology 2018).
- Created `src/rag/vector_store.py`:
  - `ChromaVectorStore`: Embedded ChromaDB vector store integration supporting both persistent storage (`data/chromadb`) and ephemeral in-memory storage for isolated evaluations.
  - Cosine distance index (`"hnsw:space": "cosine"`), document addition, batch upsert, source filtering, and thresholded semantic search.
- Created `src/rag/citation_engine.py`:
  - `CitationEngine`: Formats grounded citations, builds standardized bibliographies, and verifies provenance integrity.
  - Provenance verification: detects hallucinated citation references not present in retrieved knowledge base passages.
  - Formats grounded assistant responses with embedded numbered citations and bibliography append.
- Created `src/rag/retriever.py`:
  - `OncologyRetriever`: High-level service providing grounded oncology literature retrieval and citation binding.
  - Automatic knowledge base seeding on startup if vector collection is empty.
  - `retrieve(query)`: Semantic retrieval given clinical queries.
  - `retrieve_for_entities(entities)`: Entity-driven query synthesis generating grounded guideline passages matching extracted clinical findings (BI-RADS, TNM, biomarkers).

#### Configuration & Dependency Updates
- Added `chromadb = ">=0.5.0,<0.6.0"` to `pyproject.toml`.
- Added RAG settings to `src/core/config.py`: `chroma_persist_dir`, `rag_collection_name`, `rag_top_k`, `rag_similarity_threshold`.

#### Test Suite (`tests/test_rag.py`)
- Created `tests/test_rag.py` with 17 tests across 5 test classes (`TestBiomedicalEmbeddings`, `TestKnowledgeBase`, `TestChromaVectorStore`, `TestCitationEngine`, `TestOncologyRetriever`).
- **Total test count: 106 passing tests across 10 test modules (100% pass rate).**

---

## [0.4.0] - 2026-10-27

### Added (Phase 4 — Fine-Tune Oncology LLM Completed)

#### New Modules: LLM Training, Prompt Formatting & Evaluation (`src/training/`)
- Created `src/training/schemas.py`:
  - `InstructionCategory` (StrEnum): `BIRADS_EXPLANATION`, `TNM_REASONING`, `BIOMARKER_ANALYSIS`, `TUMOR_SUMMARY`, `LYMPH_NODE_STATUS`, `SAFETY_REFUSAL`, `PATIENT_SUMMARY`.
  - `ChatFormat` (StrEnum): `QWEN`, `LLAMA3`, `ALPACA`, `SHAREGPT`.
  - `InstructionSample`: Pydantic v2 schema for instruction-tuning prompt-response records with metadata.
  - `DatasetSplit`: Container for train/val/test partitions.
  - `TrainingConfig`: Pydantic configuration for Unsloth + PEFT QLoRA hyperparams (rank, alpha, batch size, learning rate, epochs, target projection modules, W&B logging).
  - `EvaluationResult`: Benchmark results schema tracking prompt counts, diagnostic leakage rate, disclaimer adherence, and category breakdowns.
- Created `src/training/prompt_formatter.py`:
  - `format_qwen(sample)`: Formats samples into Qwen ChatML markup (`<|im_start|>...<|im_end|>`).
  - `format_llama3(sample)`: Formats samples into Llama 3 header markup (`<|start_header_id|>...<|eot_id|>`).
  - `format_prompt(sample, format_type)`: Unified dispatcher supporting Qwen, Llama 3, Alpaca, and ShareGPT.
  - Enforced `SYSTEM_PROMPT` and `ASSISTIVE_DISCLAIMER` across all chat formatting.
- Created `src/training/dataset_validator.py`:
  - `check_for_phi(text)`: Scans for potential Protected Health Information (SSN, MRN, phone, email, patient full names).
  - `check_for_diagnostic_assertion(text)`: Scans for forbidden definitive diagnostic assertions violating Rules.md §8 (e.g., "I diagnose you with", "You definitely have cancer").
  - `has_assistive_disclaimer(text)`: Verifies required clinical disclaimer keywords.
  - `validate_dataset(samples)`: Full dataset validator returning `DatasetValidationReport`.
- Created `src/training/dataset_generator.py`:
  - `generate_instruction_samples()`: Curated clinical instruction generator covering BI-RADS (0–6), TNM staging (AJCC 8th edition), biomarkers (ER/PR/HER2/Ki-67), safety refusals, and patient summaries.
  - `create_dataset_splits(samples, train_ratio, val_ratio, seed)`: Deterministic partitioner.
  - `export_dataset_jsonl(samples, output_path)`: Exports dataset splits to JSONL.
  - Generated and exported `data/processed/train.jsonl`, `data/processed/val.jsonl`, and `data/processed/test.jsonl`.
- Created `src/training/train_qlora.py`:
  - `run_qlora_training(config, samples, dry_run)`: Standalone QLoRA training pipeline supporting Unsloth FastLanguageModel + PEFT on GPU and dry-run validation mode for CPU/CI.
  - Hardware inspection helper `check_gpu_environment()`.
  - Command-line interface with `--dry-run`, `--base-model`, `--epochs`, `--batch-size`, and `--lora-r` options.
- Created `src/training/evaluator.py`:
  - `evaluate_completion(eval_sample, completion)`: Evaluates single completions for diagnostic leakage, PHI, disclaimer presence, and expected concept coverage.
  - `evaluate_model(model_fn, eval_cases)`: Benchmark evaluation engine against held-out clinical prompts (`HELD_OUT_EVAL_CASES`).
  - Computes diagnostic leakage rate (target < 5%) and disclaimer presence rate (target >= 95%) per PRD §6.

#### Test Suite (`tests/test_training.py`)
- Created `tests/test_training.py` with 21 unit and integration tests across 5 test classes (`TestDatasetGenerator`, `TestPromptFormatter`, `TestDatasetValidator`, `TestQLoRATrainingPipeline`, `TestEvaluatorHarness`).
- **Total test count: 89 passing tests across 9 test suites (100% pass rate).**

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
