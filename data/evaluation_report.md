# Aviothic Breast Cancer Report Copilot — System Evaluation Report

**Evaluation Date:** 2026-10-27 19:05:30 UTC  
**Overall PRD §6 Status:** **PASSED**

---

## 1. Summary of PRD §6 Target Compliance

| PRD §6 Metric | Target Threshold | Measured Value | Status |
|---|---|---|---|
| Extraction Macro Precision | ≥ 0.85 | 1.0000 | ✅ PASS |
| Extraction Macro Recall | ≥ 0.85 | 1.0000 | ✅ PASS |
| Hallucination Rate | < 0.05 (< 5%) | 0.0% | ✅ PASS |
| Diagnostic Leakage Rate | < 0.05 (< 5%) | 0.0% | ✅ PASS |
| Disclaimer Presence Rate | ≥ 0.95 (≥ 95%) | 100.0% | ✅ PASS |
| Ingestion + Extraction Latency (p95) | ≤ 30,000 ms (30s) | 2.42 ms | ✅ PASS |
| Conversational Turn Latency (p95) | ≤ 5,000 ms (5s) | 12.34 ms | ✅ PASS |

---

## 2. Clinical Entity Extraction Breakdown

| Entity Category | True Positives | False Positives | False Negatives | Precision | Recall | F1 Score |
|---|---|---|---|---|---|---|
| `birads` | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `tnm_staging` | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `biomarkers` | 4 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `tumor_dimensions` | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| `lymph_nodes` | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

**Macro F1:** 1.0000 across 13 gold entities evaluated.

---

## 3. Latency Distribution Profiling

| Operation | Sample Count | Mean (ms) | p50 (ms) | p90 (ms) | p95 (ms) | Max (ms) | Target p95 |
|---|---|---|---|---|---|---|---|
| Ingestion & Extraction | 10 | 1.92 | 1.92 | 2.35 | 2.42 | 2.42 | ≤ 30000 ms |
| Conversational Turn | 10 | 8.70 | 8.02 | 9.86 | 12.34 | 12.34 | ≤ 5000 ms |

---

## 4. Clinical Safety & Boundary Verification
- **Non-Diagnostic Policy:** 100% of tested turns verified non-diagnostic without malignancy claims.
- **Assistive Disclaimer:** Mandatory disclaimer validated across all assistant outputs.
- **Citation Provenance:** Grounding citations audited against verified guideline indices.