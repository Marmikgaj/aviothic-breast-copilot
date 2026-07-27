# PRD.md — Aviothic Breast Cancer Report Copilot

**Version:** 1.0 (Draft) · **Date:** July 2026 · **Owner:** Solo developer + AI pair-programming

---

## 1. Problem Statement

Radiologists and pathologists reading breast imaging and pathology reports spend significant non-billable time manually re-reading heterogeneous documents (mammography, ultrasound, MRI, PET-CT, pathology) to extract structured data points — BI-RADS category, TNM stage, tumor size, biomarker status (ER/PR/HER2/Ki-67), lymph node involvement, and follow-up recommendations. This is slow, error-prone, and produces no reusable structured record. Existing tools are either generic NLP pipelines (not tuned to breast-cancer-specific vocabulary and reporting conventions) or commercial black-box products that clinicians can't inspect, self-host, or trust with unclear grounding.

Aviothic is a copilot, not a diagnostician: it reads what's already written in a report, organizes it into structured fields, and lets the clinician ask grounded follow-up questions — with every claim traceable back to the source report or a cited guideline.

## 2. Target User Personas

**Primary — Dr. Sarah Chen, breast imaging radiologist, academic medical center.**
Reads 20–40 reports/day across modalities. Needs to quickly cross-reference a patient's current report against prior reports, get a plain-English staging explanation to sanity-check her own read, and produce a structured summary she can paste into her dictation or EHR note. Time-pressured; will not tolerate a tool that requires manual re-typing of data already in the report.

**Secondary — Dr. James Okonkwo, pathologist, community hospital.**
Lower report volume but more heterogeneous document quality (scanned faxes, inconsistent templates). Wants reliable OCR + extraction on messy inputs, and a patient-friendly summary he can hand to a patient during a consult without rewriting it himself.

## 3. Core Value Proposition

Compared to the alternatives:
- **vs. manual abstraction:** eliminates repetitive re-reading and transcription of structured fields.
- **vs. generic NLP/LLM tools:** entity extraction is tuned to breast-cancer-specific schemas (BI-RADS, TNM, biomarkers) and grounded via RAG against trusted oncology sources rather than general-purpose knowledge.
- **vs. commercial black-box products:** self-hosted, open-weight, inspectable pipeline — every answer cites its source (report text or retrieved guideline passage), and nothing is generated as a "diagnosis."

## 4. Feature List

### Must-Have (v1)
- PDF/image upload (single report at a time, session-scoped)
- OCR pipeline (Tesseract + PyMuPDF) with confidence scoring and raw-text fallback on low-confidence extraction
- Structured entity extraction: BI-RADS, TNM staging, tumor size, biomarkers (ER/PR/HER2/Ki-67), lymph node status, recommendations
- Session-based patient context memory (holds all reports uploaded in one working session)
- Conversational Q&A grounded in the uploaded report(s) + RAG-retrieved guideline/PubMed context, with inline citations
- Structured JSON export (for downstream EHR copy/paste or integration)
- Clinician-facing structured summary (dense, technical)
- Patient-friendly summary generation (plain-language, for the clinician to review and hand to the patient — **not sent directly to any patient by the system**)
- Safety/citation layer enforcing "assistive, not diagnostic" framing on every generated output
- REST API as the primary interface; a minimal web dashboard consumes the same API

### Should-Have (v2)
- Compare-two-reports mode (e.g., prior vs. current mammogram)
- Persistent, longitudinal patient timeline across multiple visits/sessions (requires a real patient-identity + consent model, deferred deliberately — see §7)
- Multi-tenant deployment (isolated per hospital/practice)
- EHR bidirectional write-back
- Fine-tuning refinements for sub-specialty report formats (e.g., breast MRI structured reporting templates)

### Won't-Have (explicitly out of scope, v1 and v2)
- **Not** an automated diagnostic tool — never outputs a diagnosis or malignancy determination
- **Not** a patient self-service portal — patients never query the copilot directly; all patient-facing content is clinician-mediated
- **Not** a billing/coding assistant
- **Not** real-time DICOM image stream analysis (only DICOM structured *reports*, if available, as text — not pixel-level image interpretation)
- **Not** a cohort-level analytics/population-health tool

## 5. Key User Flows

1. **Upload → structured JSON:** Clinician uploads a report (PDF or scanned image) → system runs OCR if needed → text cleaning → entity extraction → clinician sees structured fields + confidence flags → can export JSON.
2. **Grounded follow-up Q&A:** Clinician asks "What does this BI-RADS 4 mean for next steps?" → system answers using (a) the report's own text and (b) RAG-retrieved guideline passages → every claim is cited → answer is flagged as assistive.
3. **Patient-friendly summary:** Clinician requests a plain-language version of the current report → system generates a summary with a mandatory "discuss this with your doctor" disclaimer → clinician reviews and decides whether/how to share it.
4. **Multi-report session comparison (v1-lite):** Within a single session, clinician uploads two reports for the same patient and asks the copilot to note differences — full structured "compare" mode is v2, but grounded Q&A across both uploaded reports is in scope for v1 since context memory already holds them.

## 6. Success Metrics (draft targets — revisit after Phase 8 evaluation)

| Metric | Target |
|---|---|
| Entity extraction precision/recall (BI-RADS, TNM, tumor size) | ≥ 0.85 on held-out annotated set |
| Hallucination rate (claims without a valid citation) | < 5%, measured via manual clinical-review sampling |
| Report ingestion + extraction latency | ≤ 30s p95 for a typical single-report PDF |
| Conversational turn latency | ≤ 5s p95 |
| Clinician review satisfaction (pilot) | Positive feedback on ≥ 80% of reviewed sessions |

## 7. Assumptions & Open Questions

These are explicit assumptions made to unblock Phase 1–2 work; flag any of these to change direction before Phase 3+:

- **Patient identity/persistence:** v1 uses session-scoped context only — no persistent patient ID or cross-visit history is stored, to minimize PII/HIPAA storage burden. Longitudinal patient timelines are a v2 feature requiring a real consent + identity model.
- **Concurrency scale:** designed for a single small deployment — a handful of concurrent users and on the order of dozens of reports/day, consistent with a single-GPU-node inference setup.
- **Guideline licensing:** assumes use of publicly available NCCN/ASCO guideline excerpts and PubMed/PMC open-access abstracts for RAG; any licensed guideline content requires separate legal review before indexing.
- **Annotated training/eval data:** assumes CBIS-DDSM and VinDr-Mammo (imaging) plus synthetic instruction data are sufficient for initial fine-tuning; a held-out manually annotated report set is still needed for extraction evaluation and does not yet exist — flagged as a Phase 3/8 risk.
- **Timeline:** open-ended, phase-by-phase, no fixed calendar deadline.
