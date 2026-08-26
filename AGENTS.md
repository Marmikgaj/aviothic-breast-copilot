# AGENTS.md — AI Agent Operating Instructions & System Guidelines

This document defines the operating rules, technical architecture, and pair-programming guidelines for AI Agents (Copilots, Code Generators, and Automated Assistants) working on the **Aviothic Breast Cancer Report Copilot** codebase.

---

## 1. Core Principles & Philosophy

1. **Assistive, NOT Diagnostic**: The system NEVER generates a clinical diagnosis or definitive malignancy determination. All outputs organize, explain, and extract facts already present in clinical reports or retrieved oncology guidelines.
2. **Safety & Grounding First**: Every clinical claim produced by an LLM component MUST be traceable back to either an uploaded report text offset or a retrieved guideline/PubMed citation.
3. **Auditable Extraction**: Structured extraction for critical clinical fields (BI-RADS, TNM staging, biomarkers) uses deterministic, rule-based parsers (spaCy + regex) rather than unconstrained free-text LLM generation.
4. **PHI & Privacy Protection**: No real patient data in code, tests, or vector indexes. Session data is ephemeral and session-scoped.

---

## 2. Agent Responsibilities & Workflows

When taking on a task in this repository:
- **Consult `TASKS.md`**: Review pending tasks, pick the next sequential item, and update task status upon completion.
- **Maintain `CHANGELOG_AI.md`**: Log all code additions, architectural changes, refactorings, and test suite updates.
- **Follow `docs/specs/` Specifications**: Adhere strictly to [PRD.md](docs/specs/PRD.md), [Architecture.md](docs/specs/Architecture.md), [Phases.md](docs/specs/Phases.md), [Rules.md](docs/specs/Rules.md), [Decisions.md](docs/specs/Decisions.md), and [Context.md](docs/specs/Context.md).
- **Run & Maintain Test Suite**: Ensure all existing tests pass (`.venv/bin/pytest` or `uv run pytest`). Add comprehensive unit tests for any new feature or bugfix.

---

## 3. Tech Stack & Environment Quick Reference

- **Runtime**: Python 3.12+ (managed via `uv` or virtualenv `.venv`)
- **API Framework**: FastAPI (async) with Pydantic v2 schemas
- **PDF & OCR**: PyMuPDF (`fitz`), `pdfplumber`, `pytesseract`
- **NLP & NER**: `spacy` (en_core_web_sm / custom medical rules)
- **Vector DB & RAG**: `chromadb`, `sentence-transformers` (`bge-large-en` / `BioClinicalBERT`)
- **LLM & Fine-Tuning**: Qwen3-8B / Llama3-8B fine-tuned with Unsloth + PEFT (QLoRA), served via `vLLM`
- **Logging & Config**: `structlog`, `pydantic-settings`
- **Testing & Formatting**: `pytest`, `ruff`, `black`, `mypy`

---

## 4. Current System Implementation Status

- **Phase 1 (Data Ingestion & Preprocessing)**: **COMPLETED**
  - Robust file upload validation (MIME type check, 10MB file size limit).
  - PyMuPDF text extractor for native PDFs (`src/ingestion/pdf_extractor.py`).
  - Text normalization & cleaning pipeline (`src/ingestion/text_cleaner.py`).
  - Regex-based report modality classifier (`src/ingestion/report_classifier.py`).
  - Clinical date extraction engine (`src/ingestion/date_extractor.py`).
  - Pipeline orchestration service (`src/ingestion/pipeline.py`).
  - FastAPI endpoints (`/health`, `/api/v1/upload`) with API Key authentication middleware.
  - Automated test suite: **50 passing tests** across 6 test modules in `tests/`.

---

## 5. Development Rules & Execution Commands

### Running Tests
```bash
.venv/bin/pytest
# or with uv:
uv run pytest tests/ -v
```

### Running Local API Server
```bash
.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Services
```bash
docker compose up --build
```

---

## 6. Forbidden Actions for Agents

- **NEVER** output or imply a clinical diagnosis or definitive malignancy determination.
- **NEVER** bypass API key or JWT authentication middleware.
- **NEVER** use real patient data or un-blinded PHI in test fixtures or code.
- **NEVER** add unapproved dependencies without updating `pyproject.toml` and seeking human review.
- **NEVER** use `print()` for logging — use `structlog` (`src/core/logging.py`).
