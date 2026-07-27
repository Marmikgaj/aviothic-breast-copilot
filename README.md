# Aviothic Breast Cancer Report Copilot

AI-powered clinical copilot that analyzes breast imaging and pathology reports, extracts structured clinical entities, and supports grounded follow-up conversation.

> **⚠️ This is an assistive tool, not a diagnostic system.** It organizes and explains information already present in clinical reports — it does not replace clinical judgment.

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
# Clone and enter the project
cd aviothic-breast-copilot

# Copy environment template
cp .env.example .env
# Edit .env and set a real AVIOTHIC_API_KEY

# Install dependencies
uv sync --all-extras

# Run the development server
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
cp .env.example .env
# Edit .env with real values

docker compose up --build
```

### Run Tests

```bash
uv run pytest tests/ -v
```

## API Endpoints (Phase 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (no auth) |
| `POST` | `/api/v1/upload` | Upload a report PDF |
| `GET` | `/api/v1/reports/{report_id}/status` | Poll processing status |

All endpoints except `/health` require an `X-API-Key` header.

## Project Structure

```
src/
├── api/          # FastAPI routers, middleware, schemas
├── core/         # Config, logging, exceptions
└── ingestion/    # Upload validation, PDF extraction, text cleaning
```

## Documentation

- [PRD](docs/specs/PRD.md) — Product requirements
- [Architecture](docs/specs/Architecture.md) — System design
- [Design](docs/specs/Design.md) — Visual system
- [Phases](docs/specs/Phases.md) — Build roadmap
- [Rules](docs/specs/Rules.md) — Operating boundaries

## License

Proprietary — Aviothic Clinical AI Systems
