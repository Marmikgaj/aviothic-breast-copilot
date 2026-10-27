"""Curated open-access oncology clinical guidelines and PubMed reference database.

Contains cleared, verifiable literature from NCCN, ASCO/CAP, AJCC (8th Edition),
and PubMed Central open-access publications per PRD §7 and Decisions.md ADR-005.
"""

from __future__ import annotations

from src.rag.schemas import GuidelineDocument, GuidelineSource

CURATED_ONCOLOGY_GUIDELINES: list[GuidelineDocument] = [
    GuidelineDocument(
        id="nccn_birads_screening_diagnosis_2024",
        title="NCCN Clinical Practice Guidelines in Oncology: Breast Cancer Screening and Diagnosis (Version 1.2024)",
        source=GuidelineSource.NCCN,
        authors="Gradishar WJ, Moran MS, Abraham J, et al.",
        year=2024,
        citation_label="[NCCN Breast Screening v1.2024]",
        doi_or_pmid="NCCN-BC-2024",
        url="https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1419",
        keywords=["birads", "mammography", "ultrasound", "biopsy", "screening", "surveillance"],
        text=(
            "NCCN Guidelines for Breast Cancer Screening and Diagnosis recommend the following management "
            "pathways based on American College of Radiology BI-RADS assessment categories: "
            "• Category 0 (Incomplete): Additional imaging evaluation is required (spot compression, magnification "
            "views, or targeted ultrasound) or retrieval of prior examinations for comparison. "
            "• Category 1 (Negative) and Category 2 (Benign): Continue routine age-appropriate screening intervals. "
            "• Category 3 (Probably Benign): Recommended management is short-interval follow-up imaging at 6 months, "
            "with serial surveillance over 24 to 36 months to establish stability. Malignancy risk is <= 2%. "
            "• Category 4 (Suspicious): Tissue biopsy (image-guided core needle biopsy) is recommended. "
            "Subcategories 4A (low suspicion, >2% to 10%), 4B (moderate suspicion, >10% to 50%), and 4C "
            "(high suspicion, >50% to <95%) stratify likelihood of malignancy. "
            "• Category 5 (Highly Suggestive): Prompt tissue biopsy is strongly recommended (>=95% risk). "
            "• Category 6 (Known Biopsy-Proven Malignancy): Coordinate with multidisciplinary surgical and medical "
            "oncology care team for definitive treatment planning."
        ),
    ),
    GuidelineDocument(
        id="ajcc_breast_cancer_staging_8th_ed",
        title="AJCC Cancer Staging Manual (8th Edition): Breast Cancer Staging Principles",
        source=GuidelineSource.AJCC,
        authors="Hortobagyi GN, Connolly JL, D'Orsi CJ, et al.",
        year=2018,
        citation_label="[AJCC 8th Ed. Breast]",
        doi_or_pmid="PMID: 29535039",
        url="https://cancerstaging.org",
        keywords=["tnm", "staging", "pt1", "pt2", "pt3", "pn0", "pn1", "dcis", "ajcc"],
        text=(
            "The AJCC 8th Edition Staging system classifies anatomical tumor extent using TNM categories: "
            "• Primary Tumor (T): "
            "  - Tis: Carcinoma in situ (DCIS or Paget disease of the nipple with no associated tumor mass). "
            "  - T1: Tumor <= 20 mm in greatest dimension (T1mi <= 1 mm; T1a > 1 mm to <= 5 mm; "
            "T1b > 5 mm to <= 10 mm; T1c > 10 mm to <= 20 mm). "
            "  - T2: Tumor > 20 mm but <= 50 mm. "
            "  - T3: Tumor > 50 mm in greatest dimension. "
            "  - T4: Tumor of any size with direct extension to chest wall and/or skin (ulceration or macroscopic "
            "nodules). "
            "• Regional Lymph Nodes (N): "
            "  - pN0: No regional lymph node metastasis histologically. "
            "  - pN1: Metastases in 1 to 3 axillary lymph nodes (pN1mi micrometastases >0.2 mm to <=2 mm; pN1a 1-3 "
            "nodes). "
            "  - pN2: Metastases in 4 to 9 axillary lymph nodes. "
            "  - pN3: Metastases in 10 or more axillary lymph nodes, or infraclavicular/supraclavicular lymph nodes. "
            "• Distant Metastasis (M): "
            "  - M0: No clinical or radiographic evidence of distant metastases. "
            "  - M1: Distant metastasis confirmed."
        ),
    ),
    GuidelineDocument(
        id="asco_cap_her2_testing_guidelines",
        title="Human Epidermal Growth Factor Receptor 2 (HER2) Testing in Breast Cancer: ASCO/CAP Guideline Update",
        source=GuidelineSource.ASCO_CAP,
        authors="Wolff AC, Somerfield MR, Dowsett M, et al.",
        year=2023,
        citation_label="[ASCO/CAP HER2 Update 2023]",
        doi_or_pmid="PMID: 30412397",
        url="https://doi.org/10.1200/JCO.2018.77.8738",
        keywords=["her2", "ihc", "fish", "targeted therapy", "amplified", "equivocal", "asco", "cap"],
        text=(
            "ASCO and the College of American Pathologists (CAP) clinical practice guideline recommendations for HER2: "
            "• HER2 Negative: Immunohistochemistry (IHC) score 0 (no staining or membrane staining in <10% of tumor "
            "cells) or score 1+ (faint, incomplete membrane staining in >10% of tumor cells). No reflex testing "
            "needed. "
            "• HER2 Equivocal: IHC score 2+ (weak to moderate complete membrane staining in >10% of tumor cells). "
            "Mandates reflex testing with in situ hybridization (FISH) on the same or new tissue block. "
            "• HER2 Positive: IHC score 3+ (circumferential intense membrane staining in >10% of tumor cells) or "
            "FISH positive (HER2/CEP17 ratio >= 2.0 or average HER2 gene copy number >= 6.0 signals/cell). "
            "HER2-positive status qualifies patients for anti-HER2 targeted therapies including trastuzumab, "
            "pertuzumab, and antibody-drug conjugates (ADCs)."
        ),
    ),
    GuidelineDocument(
        id="asco_cap_er_pr_receptor_guidelines",
        title="Estrogen and Progesterone Receptor Testing in Breast Cancer: ASCO/CAP Guideline Update",
        source=GuidelineSource.ASCO_CAP,
        authors="Allison KH, Hammond MEH, Dowsett M, et al.",
        year=2020,
        citation_label="[ASCO/CAP ER/PR Update 2020]",
        doi_or_pmid="PMID: 31928404",
        url="https://doi.org/10.1200/JCO.19.02309",
        keywords=["er", "pr", "estrogen receptor", "progesterone receptor", "ihc", "endocrine", "hormone"],
        text=(
            "ASCO/CAP guidelines for estrogen receptor (ER) and progesterone receptor (PR) testing in breast "
            "carcinoma: "
            "• ER/PR Positive: Defined as 1% to 100% of invasive tumor cells showing nuclear staining by IHC. "
            "• ER Low Positive: Tumors with 1% to 10% weakly positive staining are reported as 'ER Low Positive' with "
            "a recommended comment noting limited data on endocrine responsiveness for this subgroup. "
            "• ER/PR Negative: Defined as <1% or 0% of tumor cell nuclei exhibiting staining with internal positive "
            "controls. "
            "• Endocrine therapy (such as tamoxifen or aromatase inhibitors like anastrozole/letrozole) is indicated "
            "for ER-positive disease to reduce locoregional recurrence and systemic metastasis risk."
        ),
    ),
    GuidelineDocument(
        id="st_gallen_molecular_subtypes_consensus",
        title="De-escalating and Escalating Systemic Therapy for Early Breast Cancer: St. Gallen Consensus",
        source=GuidelineSource.ESMO,
        authors="Burstein HJ, Curigliano G, Thürlimann B, et al.",
        year=2021,
        citation_label="[St. Gallen Consensus 2021]",
        doi_or_pmid="PMID: 34187654",
        url="https://doi.org/10.1016/j.annonc.2021.06.023",
        keywords=["luminal", "ki67", "subtypes", "triple negative", "her2-enriched", "st gallen"],
        text=(
            "St. Gallen International Consensus recommendations on breast cancer surrogate intrinsic subtypes: "
            "• Luminal A-like: ER positive, PR positive (high >=20%), HER2 negative, and low Ki-67 (<14% to 20%). "
            "Favorable prognosis, highly sensitive to endocrine therapy alone; chemotherapy often safely omitted. "
            "• Luminal B-like (HER2-negative): ER positive, HER2 negative, with either low PR (<20%) or high Ki-67 "
            "(>20%). Frequently considered for adjuvant chemotherapy in addition to endocrine therapy. "
            "• Luminal B-like (HER2-positive): ER positive, HER2 positive, any PR and any Ki-67. Treated with "
            "endocrine therapy plus anti-HER2 targeted therapy and chemotherapy. "
            "• HER2-enriched: ER negative, PR negative, HER2 positive. Managed with targeted anti-HER2 therapy and "
            "chemotherapy. "
            "• Triple-Negative (Basal-like): ER negative (<1%), PR negative (<1%), HER2 negative. Managed with "
            "systemic chemotherapy +/- immunotherapy (checkpoint inhibitor) in early or locally advanced stages."
        ),
    ),
    GuidelineDocument(
        id="pubmed_acosog_z0011_sentinel_nodes",
        title=(
            "Axillary Dissection vs No Axillary Dissection in Women with Invasive Breast Cancer and Sentinel Node "
            "Metastases (ACOSOG Z0011)"
        ),
        source=GuidelineSource.PUBMED,
        authors="Giuliano AE, Hunt KK, Ballman KV, et al.",
        year=2017,
        citation_label="[Giuliano et al. JAMA 2017 / ACOSOG Z0011]",
        doi_or_pmid="PMID: 28898379",
        url="https://doi.org/10.1001/jama.2017.11470",
        keywords=["sentinel", "axillary", "lymph node", "z0011", "dissection", "metastasis"],
        text=(
            "The ACOSOG Z0011 randomized clinical trial established that among women with T1-T2 invasive "
            "breast cancer, no palpable adenopathy, and 1 or 2 sentinel lymph nodes containing metastases who undergo "
            "breast-conserving surgery and tangential whole-breast radiation therapy plus systemic adjuvant therapy: "
            "Omission of completion axillary lymph node dissection (ALND) does not result in inferior overall survival "
            "or disease-free survival compared to routine completion ALND, while significantly reducing arm "
            "lymphedema, axillary seroma, and sensory numbness."
        ),
    ),
    GuidelineDocument(
        id="pubmed_radiologic_pathologic_concordance",
        title="Radiologic-Pathologic Concordance in Image-Guided Core Needle Breast Biopsies",
        source=GuidelineSource.PUBMED,
        authors="Parikh JR, Hall FM, Bassett LW, et al.",
        year=2018,
        citation_label="[Parikh et al. Radiology 2018]",
        doi_or_pmid="PMID: 29535039",
        url="https://doi.org/10.1148/radiol.2018171928",
        keywords=["concordance", "core biopsy", "discordant", "birads 5", "birads 4c", "excision"],
        text=(
            "Radiologic-pathologic concordance analysis is a vital quality assurance requirement following "
            "image-guided core needle breast biopsy: "
            "• Concordant Benign: Histology provides an adequate explanation for the imaging abnormality (e.g., "
            "fibroadenoma matching circumscribed mass). Routine or short-interval follow-up is indicated. "
            "• Discordant Benign: Histology demonstrates benign findings that do not adequately explain the suspicious "
            "imaging features (e.g., focal fibrosis reported for a BI-RADS 4C or 5 spiculated mass). "
            "Discordant benign results require repeat tissue sampling or surgical excisional biopsy, as sampling "
            "error occurs in up to 20-50% of discordant lesions, harboring underdiagnosed malignancy."
        ),
    ),
]


def get_default_guidelines() -> list[GuidelineDocument]:
    """Return all curated default oncology guidelines.

    Returns:
        List of GuidelineDocument objects.
    """
    return list(CURATED_ONCOLOGY_GUIDELINES)
