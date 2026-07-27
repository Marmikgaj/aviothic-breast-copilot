# Architecture.md — Aviothic Breast Cancer Report Copilot

## 1. High-Level Architecture

```
                         ┌─────────────────────────┐
                         │   Client (API consumer   │
                         │  or minimal web dashboard)│
                         └────────────┬─────────────┘
                                      │ HTTPS / REST + JSON
                                      ▼
                         ┌─────────────────────────┐
                         │        FastAPI           │
                         │  (auth, routing, async)  │
                         └────────────┬─────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
   ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
   │  Document Ingestion │  │   Safety & Citation │  │  Patient Context    │
   │  (upload, validate) │  │   Layer (guardrails) │  │  Memory (session)   │
   └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘
              ▼                        │                        │
   ┌────────────────────┐              │                        │
   │   OCR Pipeline       │             │                        │
   │ (Tesseract+PyMuPDF)  │             │                        │
   └──────────┬──────────┘              │                        │
              ▼                        │                        │
   ┌────────────────────┐              │                        │
   │ Text Cleaning        │             │                        │
   └──────────┬──────────┘              │                        │
              ▼                        │                        │
   ┌────────────────────┐              │                        │
   │ Entity Extraction    │             │                        │
   │ (spaCy + rules)      │             │                        │
   └──────────┬──────────┘              │                        │
              ▼                        │                        │
   ┌──────────────────────────────────────────────────────────────────┐
   │                     LLM Reasoning (vLLM-served,                   │
   │                fine-tuned Qwen3-8B/Llama3-8B via QLoRA)           │
   └───────────────────────────────┬────────────────────────────────┬─┘
                                    │                                │
                                    ▼                                ▼
                       ┌────────────────────┐          ┌────────────────────┐
                       │   RAG Engine        │          │ Conversation Engine │
                       │ (ChromaDB + bge-    │◄─────────┤  (multi-turn chat,  │
                       │  large-en/BioClin-  │          │   grounded in report │
                       │  icalBERT embeds)   │          │   + RAG context)     │
                       └────────────────────┘          └──────────┬──────────┘
                                                                    ▼
                                                        ┌────────────────────┐
                                                        │ Structured Report    │
                                                        │ Generator (JSON +    │
                                                        │ clinician summary +  │
                                                        │ patient-friendly     │
                                                        │ summary)             │
                                                        └────────────────────┘
```

All stages after upload are wrapped by the **Safety & Citation Layer**, which enforces that no LLM output reaches the client without an "assistive, not diagnostic" tag and, where applicable, a source citation.

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.11 | Required; mature ecosystem for ML/NLP tooling |
| API framework | FastAPI (async) | Native async support for long-running OCR/extraction jobs; automatic OpenAPI schema fits the API-first priority |
| LLM | Qwen 3 8B or Llama 3 8B | Open-weight — required for self-hosting, no PHI leaves the deployment |
| Fine-tuning | Unsloth + PEFT (QLoRA) | Memory-efficient fine-tuning on a single GPU, fits solo-dev/single-node budget |
| Inference server | vLLM | High-throughput batched inference, OpenAI-compatible API surface |
| Embeddings | bge-large-en or BioClinicalBERT | Strong general + biomedical-domain embedding options; swappable per RAG eval results |
| Vector DB | ChromaDB | Lightweight, embeddable, no separate infra service required — fits single-node deployment |
| OCR | Tesseract + PyMuPDF | Open-source, no external API calls (PHI stays local) |
| PDF parsing | pdfplumber / PyMuPDF | Handles both text-native and table-heavy PDFs |
| NER | spaCy + custom medical rules | Deterministic, auditable extraction for safety-critical fields (BI-RADS, TNM) rather than relying solely on LLM extraction |
| Experiment tracking | Weights & Biases | Tracks fine-tuning runs, extraction eval metrics |
| Containerization | Docker | Reproducible deploys to RunPod/Vast.ai |
| Deployment | RunPod (dedicated GPU pod, default) / Vast.ai (spot, for training) | See §6 for reasoning |

## 3. Folder Structure

```
aviothic-copilot/
├── src/
│   ├── ingestion/        # upload handling, file validation, MIME/size checks
│   ├── ocr/              # Tesseract/PyMuPDF pipeline, confidence scoring
│   ├── extraction/        # spaCy pipelines + custom rules for BI-RADS/TNM/biomarkers
│   ├── rag/               # ChromaDB indexing, retrieval, citation formatting
│   ├── conversation/       # chat session logic, context assembly, prompt templates
│   ├── context/            # PatientContext memory builder (session-scoped)
│   ├── safety/             # guardrails, output validation, citation enforcement
│   ├── reporting/          # structured JSON + clinician summary + patient summary generators
│   ├── api/                # FastAPI routers, request/response schemas (Pydantic)
│   └── core/               # config, logging (structlog), shared utilities
├── models/                 # fine-tuned weights — NOT in git, versioned via DVC/artifact storage
├── data/
│   ├── raw/                 # gitignored — source reports/datasets
│   └── processed/           # cleaned/annotated datasets for eval and fine-tuning
├── tests/                   # mirrors src/ structure
├── deploy/                  # Dockerfile, RunPod/Vast.ai configs, CI/CD
└── notebooks/                # exploratory work, not production code
```

## 4. Data Model Overview

- **PatientContext** — session-scoped container: `session_id`, list of `Report` objects, `ConversationTurn` history, created/updated timestamps. No persistent cross-session patient identifier in v1 (see PRD §7).
- **Report** — `report_id`, `modality` (mammography/ultrasound/MRI/PET-CT/pathology), `raw_text`, `ocr_confidence`, `upload_timestamp`, list of `ExtractedEntity`.
- **ExtractedEntity** — `entity_type` (e.g., `bi_rads`, `tnm_stage`, `tumor_size`, `biomarker`, `lymph_node_status`), `value`, `source_span` (text offset in `raw_text`), `confidence`.
- **ConversationTurn** — `turn_id`, `role` (user/assistant), `content`, list of `Citation`, `timestamp`.
- **Citation** — `source_type` (report | guideline | pubmed), `source_id`, `text_snippet` (short, non-reproducing reference), `retrieval_score`.
- **StructuredSummary** — `report_ids` covered, `clinician_summary` (technical), `patient_summary` (plain-language, includes disclaimer text), `export_json`.

## 5. API Contract Overview

All endpoints are versioned under `/api/v1/`. Long-running operations (OCR + extraction) are async with a polling or webhook pattern.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/upload` | POST | Upload a report file; returns `report_id` + async job status |
| `/api/v1/reports/{report_id}/status` | GET | Poll OCR/extraction job status |
| `/api/v1/reports/{report_id}/entities` | GET | Retrieve structured extracted entities |
| `/api/v1/sessions/{session_id}/chat` | POST | Send a conversational turn; returns grounded answer + citations |
| `/api/v1/sessions/{session_id}/summary` | POST | Generate clinician + patient-friendly summaries |
| `/api/v1/sessions/{session_id}/export` | GET | Export structured JSON for the session |

All request/response bodies are Pydantic v2 models; auth via API key or JWT (see Rules.md §5).

## 6. Key Architectural Decisions & Trade-offs

- **Open-weight LLM vs. hosted API:** required for PHI to never leave the deployment boundary; trade-off is more ops burden (fine-tuning, serving) vs. a hosted API.
- **ChromaDB vs. Pinecone/Weaviate:** ChromaDB runs embedded/local with no extra infra service, fitting a single-node deployment; trade-off is less horizontal scalability, acceptable at current scale (see PRD §7 concurrency assumption).
- **spaCy + rules vs. end-to-end LLM extraction:** deterministic rule-based extraction for safety-critical structured fields (BI-RADS, TNM) is more auditable and testable than relying on LLM free-text parsing; the LLM is instead used for reasoning/conversation on top of already-extracted, verified entities.
- **FastAPI vs. Flask/Django:** native async fits long-running OCR/extraction and concurrent chat sessions; automatic OpenAPI schema supports the API-first priority.
- **RunPod dedicated pod (default) vs. serverless:** a fine-tuned model served continuously via vLLM benefits from a warm, always-on pod to avoid cold-start latency hurting multi-turn conversation UX; Vast.ai spot instances are better suited to the cheaper, interruption-tolerant fine-tuning/training jobs rather than live inference serving.

## 7. Scalability & Performance Notes

- Single-node GPU deployment; vLLM's continuous batching handles the low concurrency assumed in PRD §7 without needing multi-node scaling.
- ChromaDB embedding cache avoids re-embedding repeated guideline lookups across sessions.
- Target: report ingestion/extraction ≤ 30s p95, chat turn ≤ 5s p95 (see PRD §6). Revisit if concurrency assumptions change.
