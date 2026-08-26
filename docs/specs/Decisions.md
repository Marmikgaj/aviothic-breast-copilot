# Decisions.md — Architectural Decision Records (ADRs)

This document records the key architectural, technical, and domain design decisions made for the **Aviothic Breast Cancer Report Copilot**.

---

## ADR-001: Native PDF Extraction via PyMuPDF with OCR Fallback Strategy

* **Status:** Accepted (Implemented in Phase 1)
* **Context:** Breast cancer clinical reports are distributed primarily as PDFs. Some are text-native (generated directly by electronic health record systems), while others are scanned images or faxes.
* **Decision:** Use PyMuPDF (`fitz`) as the primary fast text extractor. If PyMuPDF extracts insufficient text (indicating a scanned image document), route the document to the Tesseract OCR fallback pipeline (Phase 2).
* **Consequences:** Provides sub-second ingestion for native PDFs while maintaining full support for legacy scanned documents. Prevents heavy OCR compute overhead on text-native files.

---

## ADR-002: Deterministic NER (spaCy + Rules) over End-to-End LLM Extraction

* **Status:** Accepted (Planned for Phase 3)
* **Context:** Clinical entities such as BI-RADS categories (0–6), TNM staging codes (e.g., T2N1M0), tumor size dimensions (e.g., 1.5 x 1.2 cm), and biomarker statuses (ER+, PR+, HER2-, Ki-67 15%) drive clinical decision-making. Relying solely on free-text LLM generation for entity extraction introduces risk of hallucinated or shifted values.
* **Decision:** Combine spaCy NLP pipelines with deterministic regular expression rules and pattern matchers for structured entity extraction. The LLM is restricted to explanation, summarization, and RAG-driven Q&A.
* **Consequences:** Extraction results are auditable, deterministic, unit-testable, and maintain explicit source character spans for verification in original reports.

---

## ADR-003: Session-Scoped Context Memory vs. Persistent Longitudinal Database

* **Status:** Accepted (Defined in PRD §7 & Architecture §4)
* **Context:** Storing persistent patient records across sessions introduces significant HIPAA/PHI compliance risk, requiring complex identity management, consent frameworks, and encrypted persistent storage.
* **Decision:** In v1, `PatientContext` is strictly session-scoped in memory (`session_id`). When a session ends or expires, the associated uploaded report texts and context memory are cleared.
* **Consequences:** Minimizes PII/PHI storage risks and legal liability. Cross-session patient timelines are explicitly deferred to v2.

---

## ADR-004: Self-Hosted Open-Weight LLM (Qwen3-8B / Llama3-8B via vLLM)

* **Status:** Accepted (Defined in Architecture §2 & PRD §3)
* **Context:** Healthcare institutions and clinicians cannot send protected health information (PHI) to external commercial LLM APIs without strict Business Associate Agreements (BAAs) and data isolation guarantees.
* **Decision:** Use open-weight 8B models (Qwen3-8B or Llama3-8B) fine-tuned via Unsloth (QLoRA) and served locally on GPU infrastructure using vLLM continuous batching.
* **Consequences:** Complete data sovereignty — no PHI leaves the deployment boundary. System can be self-hosted on dedicated GPU nodes (e.g., RunPod).

---

## ADR-005: Embedded ChromaDB Vector Engine over External Vector Services

* **Status:** Accepted (Defined in Architecture §2 & §6)
* **Context:** Vector retrieval is required to ground LLM reasoning in PubMed abstracts and clinical guidelines. External hosted vector DBs (e.g., Pinecone) add third-party dependencies and egress latency.
* **Decision:** Use ChromaDB embedded directly within the application container, leveraging `bge-large-en` or `BioClinicalBERT` embeddings.
* **Consequences:** Eliminates external vector database infrastructure management, reduces deployment complexity, and maintains single-node portability.

---

## ADR-006: Hard Boundary Safety & Citation Layer

* **Status:** Accepted (Defined in Rules.md §8 & Architecture §1)
* **Context:** LLMs can generate plausible-sounding medical advice or diagnostic assertions. Unvalidated outputs pose severe patient safety and legal risks.
* **Decision:** Implement a mandatory `Safety & Citation Layer` intercepting all LLM outputs before they reach the API response. This layer verifies citation provenance and appends mandatory "assistive, non-diagnostic" disclaimers.
* **Consequences:** No raw LLM completion can bypass safety checks. Any clinical statement lacking source grounding is flagged or blocked.

---

## ADR-007: API-First Design with FastAPI & Pydantic v2

* **Status:** Accepted (Implemented in Phase 1)
* **Context:** The system must support both minimal web UI clients and direct integration into EHR dictation or clinical workflow extensions.
* **Decision:** Build as an API-first FastAPI application, using Pydantic v2 schemas for all request/response models and `X-API-Key` authentication.
* **Consequences:** Automatic OpenAPI specs, robust runtime input validation, native async performance for long-running ingestion jobs, and clean UI/backend decoupling.
