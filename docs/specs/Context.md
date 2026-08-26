# Context.md — Domain Knowledge & Technical Context

This document provides essential medical domain knowledge, clinical reporting conventions, and technical environment context for the **Aviothic Breast Cancer Report Copilot**.

---

## 1. Clinical & Medical Domain Context

### Breast Imaging Modalities & Report Types
1. **Mammography (Diagnostic / Screening)**: Primary radiological imaging using low-dose X-rays. Key findings include masses, microcalcifications, architectural distortion, and asymmetry.
2. **Breast Ultrasound**: Sonographic imaging used to evaluate palpable masses, differentiate fluid-filled cysts from solid lesions, and guide needle biopsies.
3. **Breast MRI (Magnetic Resonance Imaging)**: High-sensitivity contrast-enhanced imaging used for high-risk screening, staging, and assessing response to neoadjuvant therapy.
4. **Histopathology / Pathology Reports**: Microscopic biopsy or surgical specimen evaluation providing definitive histological diagnosis, lesion grade, tumor type (e.g., Invasive Ductal Carcinoma - IDC, Invasive Lobular Carcinoma - ILC, DCIS), and biomarker status.
5. **PET-CT / Staging Scans**: Systemic imaging used to evaluate distant metastasis and nodal spread in advanced cases.

---

### BI-RADS (Breast Imaging-Reporting and Data System)
BI-RADS is the standardized risk assessment framework established by the American College of Radiology (ACR):

| BI-RADS Category | Clinical Assessment | Malignancy Risk | Recommended Management |
|---|---|---|---|
| **Category 0** | Incomplete — Needs additional imaging evaluation | N/A | Recall for additional views / ultrasound |
| **Category 1** | Negative | ~0% | Routine screening |
| **Category 2** | Benign findings | ~0% | Routine screening |
| **Category 3** | Probably Benign | > 0% but ≤ 2% | Short-interval follow-up (6 months) |
| **Category 4** | Suspicious Abnormality (4A, 4B, 4C) | > 2% to < 95% | Biopsy should be considered |
| **Category 5** | Highly Suggestive of Malignancy | ≥ 95% | Biopsy / surgical action required |
| **Category 6** | Known Biopsy-Proven Malignancy | N/A | Surgical excision / definitive therapy |

---

### TNM Staging System (AJCC 8th Edition Overview)
- **T (Primary Tumor Size/Extent)**:
  - `Tis`: Carcinoma in situ (DCIS, LCIS)
  - `T1`: Tumor ≤ 20 mm (T1mi ≤ 1 mm, T1a 1-5 mm, T1b 5-10 mm, T1c 10-20 mm)
  - `T2`: Tumor > 20 mm but ≤ 50 mm
  - `T3`: Tumor > 50 mm
  - `T4`: Tumor of any size with direct extension to chest wall or skin (ulceration/edema)
- **N (Regional Lymph Nodes)**:
  - `N0`: No regional lymph node metastasis
  - `N1`: Metastasis to movable ipsilateral axillary lymph node(s)
  - `N2`: Metastasis to fixed/matted axillary nodes or internal mammary nodes
  - `N3`: Metastasis to infraclavicular, internal mammary, or supraclavicular nodes
- **M (Distant Metastasis)**:
  - `M0`: No distant metastasis
  - `M1`: Distant metastasis present (bone, lung, liver, brain, distant nodes)

---

### Biomarker Profile & Receptor Status
Pathology reports assess key prognostic and predictive biomarkers:
- **Estrogen Receptor (ER)**: Positive (+) / Negative (-), percentage expression (e.g., 90% positive).
- **Progesterone Receptor (PR)**: Positive (+) / Negative (-), percentage expression.
- **HER2 (Human Epidermal Growth Factor Receptor 2)**: Measured via IHC (0, 1+, 2+, 3+) and FISH amplification if IHC is 2+ equivocal.
- **Ki-67 Index**: Cellular proliferation marker expressed as a percentage (e.g., 25% high proliferation).
- **Molecular Subtypes**: Luminal A (ER+/PR+/HER2-/low Ki-67), Luminal B (ER+/HER2-/high Ki-67 or ER+/HER2+), HER2-enriched (ER-/PR-/HER2+), Triple Negative (ER-/PR-/HER2-).

---

## 2. Technical Context & Repository Conventions

### Repository Architecture & File Organization
```
aviothic-breast-copilot/
├── AGENTS.md                  # AI agent guidelines & state
├── TASKS.md                   # Granular task checklist & status
├── CHANGELOG_AI.md            # AI commit log & release history
├── README.md                  # Quickstart & user documentation
├── pyproject.toml             # Dependencies & pytest configuration
├── Dockerfile                 # Container packaging definition
├── docker-compose.yml         # Container orchestration setup
├── docs/
│   └── specs/
│       ├── PRD.md             # Product requirements document
│       ├── Architecture.md    # System design & component diagrams
│       ├── Design.md          # Visual interface design specs
│       ├── Phases.md          # Phase-by-phase build roadmap
│       ├── Rules.md           # Safety & operating boundaries
│       ├── Decisions.md       # Architectural Decision Records (ADRs)
│       └── Context.md         # Domain & technical context (this file)
├── src/
│   ├── main.py                # FastAPI entry point & root router
│   ├── api/                   # API routers, auth middleware, schemas
│   ├── core/                  # Configuration, logging, exception hierarchy
│   └── ingestion/             # File validator, PDF extractor, cleaner, classifier, date parser
└── tests/                     # Automated Pytest suite (50+ tests)
```

---

### Key Commands for Developers & Agents
- **Run Unit Tests**: `.venv/bin/pytest` or `uv run pytest tests/ -v`
- **Run Development Server**: `.venv/bin/uvicorn src.main:app --reload`
- **Check API Health**: `curl http://localhost:8000/health`
- **Run Docker Build**: `docker compose up --build`

---

### Key Configuration Variables (`.env`)
- `AVIOTHIC_API_KEY`: Secret key required for API authorization via `X-API-Key` header.
- `MAX_UPLOAD_SIZE_BYTES`: File size limit for uploaded PDFs (default: 10,485,760 bytes / 10MB).
- `ENVIRONMENT`: `development` | `production` | `testing`.
- `LOG_LEVEL`: `INFO` | `DEBUG` | `WARNING` | `ERROR`.
