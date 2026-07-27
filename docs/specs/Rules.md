# Rules.md — AI Operating Boundaries

This file is the single source of truth for how any AI session (or new developer) should operate in this repo. When in doubt, this file wins over convenience or speed.

## 1. Approved Libraries/Frameworks (pin versions)

- `fastapi` ^0.115
- `uvicorn[standard]` ^0.32
- `pymupdf` (fitz) ^1.24
- `pdfplumber` ^0.11
- `pytesseract` ^0.3.13
- `spacy` ^3.7
- `transformers` ^4.46
- `unsloth` (latest compatible with the target base model)
- `peft` ^0.13
- `vllm` ^0.6
- `chromadb` ^0.5
- `sentence-transformers` ^3.2
- `wandb` ^0.18
- `pydantic` ^2.9
- `pytest` ^8.3
- `black` ^24.10
- `ruff` ^0.7
- `mypy` ^1.13
- `structlog` (for logging — see §4)

New dependencies outside this list require explicit human confirmation before installation (see §8).

## 2. Explicitly Forbidden

- No `eval()` or dynamic code execution of any kind
- No raw SQL strings — use an ORM or query builder
- No hardcoded secrets, API keys, or credentials anywhere in source
- No real or realistic patient data in test fixtures — use synthetic/mocked reports only
- No unvalidated file uploads — enforce size limits and MIME-type checks before touching a file
- No synchronous, blocking I/O inside async FastAPI request handlers
- No `print()` for logging — use `structlog` (or `python-json-logger`) exclusively

## 3. Coding Style & Conventions

- PEP 8 baseline, enforced via `black` (formatting) and `ruff` (linting)
- Type hints required on all public function signatures
- Max line length: 120 characters
- Docstrings in Google style for all public modules/functions/classes
- File size soft limit: ~400 lines — refactor into smaller modules if exceeded

## 4. Error Handling Philosophy

- Fail loud in development (raise, don't swallow)
- Fail soft in production: return structured error responses, never leak stack traces to the client
- Every error is logged with a correlation ID for traceability
- OCR/extraction failures degrade gracefully: return the raw extracted text plus an explicit low-confidence warning rather than silently dropping the report

## 5. Security Musts

- All input validated via Pydantic v2 models
- Every endpoint requires an auth check (API key or JWT) — no unauthenticated routes except health checks
- Secrets loaded via environment variables only (`python-dotenv` locally; injected at runtime in deployment) — never committed
- File upload size limits and MIME-type validation enforced at the ingestion boundary
- No PII (names, MRNs, DOB, etc.) in logs or in the vector DB — de-identify before embedding
- All patient context encrypted at rest

## 6. Testing Requirements

- Unit tests required for all extraction logic and the safety/citation layer
- Integration tests required for the full upload → extract → chat flow
- Minimum 70% coverage on core modules (`extraction/`, `safety/`, `rag/`)
- Test files live in `tests/`, mirroring the `src/` structure
- Use pytest fixtures for mock reports and mock LLM responses — never real patient data

## 7. Git / Commit Conventions

- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- Branch naming: `feature/...`, `fix/...`, `docs/...`
- PRs require passing CI (lint + test) before merge
- No direct pushes to `main`

## 8. Things the AI Must NEVER Do Without Explicit Human Confirmation

- Delete database migrations or patient context schemas
- Change auth logic or API key/JWT handling
- Modify the safety/citation layer's behavior
- Install a new dependency not already listed in §1
- Push model weights or datasets to a public repository
- Change LLM fine-tuning hyperparameters
- Touch any code path that generates clinical recommendations, without review
- Generate or imply a diagnosis, or state a definitive malignancy/benignity determination
- Send a patient-friendly summary directly to a patient (all patient-facing content is clinician-mediated only)

## 9. Handling Ambiguity

When a requirement is ambiguous: **ask first.** If genuinely blocked and a decision must be made to keep moving, state the assumption explicitly in a `TODO` comment in the code and again in the PR description. Never assume the clinical validity of an extracted entity — extraction confidence is not the same as clinical correctness.

## 10. Off-Limits / Auto-Generated Paths

- `models/` — fine-tuned weights, auto-generated, versioned via DVC or artifact storage, **not** committed to git
- `data/raw/` — gitignored, source reports/datasets
- Any generated client SDKs — auto-generated from the OpenAPI schema, not hand-edited
