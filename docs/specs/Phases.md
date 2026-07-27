# Phases.md — Build Roadmap

Each phase is sized to be buildable and verifiable in a single focused session. Do not start a phase until the prior phase's manual test checklist passes.

---

## Phase 1 — Data Ingestion & Preprocessing
**Goal:** A clinician can upload a breast imaging PDF and get back cleaned text plus a minimal structured JSON (report type + date). This is the smallest vertical slice that proves the pipeline end-to-end.
**Deliverables:** `/api/v1/upload` endpoint; file validation (size/MIME); PDF text extraction (PyMuPDF/pdfplumber) for text-native PDFs; basic text cleaning; minimal JSON output `{report_type, report_date, raw_text}`.
**Dependencies:** none — first phase.
**Deferred:** OCR for scanned/image reports (Phase 2), any entity extraction beyond report type/date (Phase 3).
**Manual test checklist:**
- [ ] Upload a text-native PDF → receive cleaned text + correct report type/date
- [ ] Upload an oversized or wrong-MIME file → receive a clear validation error, not a crash
- [ ] Upload a scanned image PDF → system does not silently return garbage (explicit "OCR not yet supported" is acceptable at this phase)

## Phase 2 — OCR & Report Parser
**Goal:** Robust extraction from scanned/image-based reports, including tables, with confidence scoring.
**Deliverables:** Tesseract + PyMuPDF OCR pipeline; confidence scoring per extracted text block; table-aware parsing; graceful degradation (raw text + low-confidence warning) per Rules.md §4.
**Dependencies:** Phase 1 ingestion pipeline.
**Deferred:** DICOM-structured-report parsing (revisit if/when needed — image-level DICOM analysis is explicitly out of scope per PRD).
**Manual test checklist:**
- [ ] Upload a scanned/faxed report → get usable text with a confidence score
- [ ] Upload a low-quality scan → get raw text + explicit low-confidence warning, not a silent failure
- [ ] Table-containing report → table structure is preserved or clearly flagged

## Phase 3 — Entity Extraction ⚠️ high risk
**Goal:** Reliable extraction of BI-RADS, TNM staging, tumor size, biomarkers, and lymph node status across heterogeneous report formats.
**Deliverables:** spaCy pipeline + custom rules per entity type; `ExtractedEntity` objects with source spans and confidence; initial precision/recall evaluation against a manually annotated held-out set (see PRD §7 — this annotated set does not yet exist and must be created early in this phase).
**Dependencies:** Phase 2 clean text output.
**Deferred:** Full-schema extraction for every possible modality edge case — start with mammography/pathology, expand to MRI/PET-CT once core patterns are validated.
**Manual test checklist:**
- [ ] Run against 5–10 varied sample reports → correct BI-RADS/TNM/tumor size extracted with source spans
- [ ] Precision/recall measured against the annotated set and logged
- [ ] Low-confidence or missing fields are flagged, not silently omitted
**Risk note:** heterogeneous report formats mean rule coverage will be incomplete at first pass — start with a small spike/prototype on 2–3 real-world format variants before committing to the full rule set.

## Phase 4 — Fine-Tune Oncology LLM ⚠️ high risk
**Goal:** A QLoRA fine-tuned Qwen3-8B/Llama3-8B that reliably reasons about breast-cancer report content without hallucinating clinical facts.
**Deliverables:** Instruction dataset built from public sources (synthetic + de-identified patterns); Unsloth + PEFT (QLoRA) fine-tuning run tracked in W&B; baseline hallucination/quality evaluation.
**Dependencies:** none technically, but benefits from Phase 3's entity schema to shape instruction data.
**Deferred:** Multi-turn conversation tuning (that's largely Phase 7's job) — Phase 4 focuses on single-turn reasoning quality.
**Manual test checklist:**
- [ ] Fine-tuned model correctly explains a BI-RADS score in plain language on held-out examples
- [ ] Model does not generate a diagnosis or definitive malignancy statement in any test prompt
- [ ] W&B run logged with dataset version and hyperparameters
**Risk note:** dataset curation quality is the dominant risk here — do a small-scale fine-tune spike first to validate the data pipeline before a full run.

## Phase 5 — Build RAG
**Goal:** Retrieval-augmented generation grounded in PubMed abstracts and clinical guidelines, with citations.
**Deliverables:** ChromaDB index of PubMed/PMC open-access abstracts + available guideline excerpts; bge-large-en or BioClinicalBERT embedding pipeline; retrieval + citation formatting layer.
**Dependencies:** none blocking, but pairs naturally with Phase 4's model.
**Deferred:** Licensed guideline content requiring legal clearance (see PRD §7) — index only cleared/open-access sources for now.
**Manual test checklist:**
- [ ] Query returns relevant guideline/abstract passages with citations
- [ ] Citations point to retrievable source IDs, not fabricated references
- [ ] Retrieval latency is acceptable within the overall chat-turn latency budget

## Phase 6 — Build Patient Context Memory
**Goal:** Session-scoped `PatientContext` that holds multiple uploaded reports and makes them jointly available to the conversation engine.
**Deliverables:** `PatientContext` builder; multi-report session handling; context window management (truncation/summarization strategy when context exceeds model limits).
**Dependencies:** Phases 1–3 (needs structured entities to build context efficiently).
**Deferred:** Persistent cross-session patient timeline (v2, per PRD §7).
**Manual test checklist:**
- [ ] Upload two reports in one session → both are available to later chat queries
- [ ] Context window management doesn't silently drop clinically relevant fields
- [ ] Session data does not persist or leak across separate sessions

## Phase 7 — Conversational Assistant
**Goal:** Full grounded chat: answers reference report context + RAG, all citations enforced, safety guardrails active, and lightweight two-report comparison within a session.
**Deliverables:** `/api/v1/sessions/{id}/chat` endpoint; safety/citation layer wired into every response; in-session report comparison Q&A.
**Dependencies:** Phases 3–6.
**Deferred:** Full structured compare-two-reports mode with a dedicated UI/schema (v2, per PRD §4).
**Manual test checklist:**
- [ ] Every chat answer includes at least one citation when a clinical claim is made
- [ ] Off-context questions are explicitly flagged as outside grounded context, not answered freely
- [ ] No response states a diagnosis or definitive malignancy determination

## Phase 8 — Evaluation & Deployment
**Goal:** Production-readiness: measured extraction accuracy, hallucination rate, latency, a clinical review pass, and a working Docker deployment.
**Deliverables:** Full precision/recall report; hallucination rate measurement against PRD §6 targets; latency benchmarking; a documented clinical review protocol (even if informal for a solo-dev pilot); Docker image; RunPod/Vast.ai deployment config.
**Dependencies:** all prior phases.
**Deferred:** nothing — this is the closing phase for v1.
**Manual test checklist:**
- [ ] Metrics from PRD §6 are measured and documented (met or explicitly noted as gaps)
- [ ] End-to-end flow (upload → extract → chat → summary → export) verified in the deployed container
- [ ] Deployment guide is sufficient for someone else to redeploy from scratch
