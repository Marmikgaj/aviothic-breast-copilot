# Aviothic Breast Cancer Report Copilot

AI-powered clinical copilot that analyzes breast imaging and pathology reports, extracts structured clinical entities (BI-RADS, TNM staging, biomarkers, tumor dimensions, lymph nodes), and supports grounded clinical decision support.

> **⚠️ Assistive, NOT Diagnostic**: Per [AGENTS.md](AGENTS.md) and [Rules.md](docs/specs/Rules.md), this system organizes and extracts facts explicitly present in clinical reports — it does not generate clinical diagnoses or definitive malignancy determinations.

---

## 🚀 Implementation Progress

- [x] **Phase 1 — Data Ingestion & Preprocessing** (100% Complete)
  - Native PDF text extraction (`PyMuPDF`), text normalization, regex date detection, modality classification (`mammography`, `pathology`, `mri`, `ultrasound`, `pet_ct`, `discharge`).
- [x] **Phase 2 — OCR & Report Parser** (100% Complete)
  - PyTesseract OCR engine (`src/ingestion/ocr_engine.py`) with word-level confidence scoring and scanned document fallback.
- [x] **Phase 3 — Entity Extraction Engine** (100% Complete)
  - Deterministic clinical entity extraction using spaCy and regular expressions.
  - 100% character-level source span tracking (`start_char`, `end_char`, `snippet`) for auditable claims.
  - LangChain & LangGraph dependencies integrated for downstream RAG and conversational AI phases.
- [ ] **Phase 4 — Fine-Tune Oncology LLM** (Planned)
- [ ] **Phase 5 — Build RAG Engine** (Planned)
- [ ] **Phase 6 — Build Patient Context Memory** (Planned)
- [ ] **Phase 7 — Conversational Assistant** (Planned)
- [ ] **Phase 8 — Evaluation & Deployment** (Planned)

---

## 🛠️ Quick Start

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or `pip`
- **Tesseract OCR** (optional, for scanned documents): `sudo apt install tesseract-ocr`

### 1. Setup & Installation

```bash
# Clone repository
cd aviothic-breast-copilot

# Copy environment template
cp .env.example .env
# Set a custom AVIOTHIC_API_KEY in .env

# Install dependencies via uv
uv sync --all-extras
```

### 2. Run API Development Server

```bash
# Run FastAPI via Uvicorn
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Docker Deployment

```bash
cp .env.example .env
docker compose up --build
```

---

## 🧪 Running Tests & Verification

The repository includes a comprehensive test suite (68 unit & integration tests) covering validation, PDF parsing, OCR fallback, report classification, date extraction, and clinical entity parsing:

```bash
# Run pytest suite
uv run pytest -v
```

---

## 📡 API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Health check & service environment metadata |
| `POST` | `/api/v1/upload` | `X-API-Key` | Upload report PDF for processing |
| `GET` | `/api/v1/reports/{report_id}/status` | `X-API-Key` | Poll report status and retrieve extracted entities |

### Example Request (`curl`)

```bash
# 1. Upload sample pathology report
API_KEY=$(grep AVIOTHIC_API_KEY .env | cut -d '=' -f2)

RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@samples/sample_genuine_pathology.pdf")

REPORT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['report_id'])")

# 2. Retrieve extracted clinical entities
curl -s http://localhost:8000/api/v1/reports/$REPORT_ID/status \
  -H "X-API-Key: $API_KEY" | python3 -m json.tool
```

---

## 📁 Repository Structure

```
aviothic-breast-copilot/
├── docs/specs/           # Specification documents (PRD, Architecture, Rules, Decisions)
├── samples/              # Synthetic test PDF medical reports
├── src/
│   ├── api/              # FastAPI app, routers, middleware, Pydantic schemas
│   ├── core/             # Configuration, logging (structlog), exceptions
│   ├── extraction/       # Phase 3 Entity Parsers (BI-RADS, TNM, Biomarkers, Tumor, Lymph)
│   └── ingestion/        # PDF extraction, OCR engine, text cleaner, classifier, pipeline
├── tests/                # 68 passing unit & integration test modules
├── AGENTS.md             # AI Agent operating instructions
├── CHANGELOG_AI.md       # AI pair-programming changelog
├── TASKS.md              # Project task tracker & roadmap
└── pyproject.toml        # uv / Python project dependencies
```

---

## 📄 License

Proprietary — Aviothic Clinical AI Systems
