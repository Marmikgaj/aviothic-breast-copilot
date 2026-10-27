"""Synthetic and guideline-derived oncology instruction dataset generator.

Generates structured instruction samples covering:
- BI-RADS categorization & clinical explanations (0–6)
- TNM staging breakdowns (AJCC 8th edition rules)
- Biomarker status interpretations (ER/PR/HER2/Ki-67)
- Anatomical tumor dimensions & lymph node summaries
- Safety refusal & non-diagnostic boundaries (Rules.md §8)
- Plain-language patient summaries with mandatory disclaimers
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.training.prompt_formatter import ASSISTIVE_DISCLAIMER
from src.training.schemas import DatasetSplit, InstructionCategory, InstructionSample

# -----------------------------------------------------------------------------
# Curated Clinical Templates
# -----------------------------------------------------------------------------

_BIRADS_TEMPLATES = [
    {
        "id_prefix": "birads_0",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": (
            "What is the clinical significance of a BI-RADS Category 0 assessment on a diagnostic mammogram?"
        ),
        "context": (
            "Impression: Right breast focal asymmetry in upper outer quadrant. " "BI-RADS Category 0: Incomplete."
        ),
        "response": (
            "A BI-RADS Category 0 assessment signifies an incomplete evaluation. "
            "It indicates that the current imaging is insufficient to make a definitive radiologic assessment, "
            "and additional evaluation is required. Typical recommended next steps include additional "
            "mammographic views (such as spot compression or magnification views), targeted breast ultrasound, "
            "or retrieval of prior imaging examinations for comparison to determine if the finding is new, "
            "stable, or resolving. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "birads_1",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": (
            "Explain the management recommendation for a bilateral screening mammogram assessed as BI-RADS 1."
        ),
        "context": (
            "Bilateral screening mammography: No dominant mass, architectural distortion, or suspicious "
            "microcalcifications. Assessment: BI-RADS 1 - Negative."
        ),
        "response": (
            "A BI-RADS Category 1 assessment is completely negative. "
            "There are no masses, architectural distortions, or suspicious microcalcifications identified. "
            "The standard recommendation is to continue routine, age-appropriate breast cancer screening "
            "per established clinical guidelines (e.g., annual or biennial mammography), unless new clinical "
            "symptoms arise in the interim. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "birads_2",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": (
            "How should a breast ultrasound report with a BI-RADS 2 finding of a simple cyst be interpreted?"
        ),
        "context": (
            "Ultrasound Left Breast: Well-circumscribed, anechoic oval mass with posterior acoustic enhancement "
            "at 2 o'clock, 4 cm from nipple, measuring 1.2 cm, consistent with a simple cyst. BI-RADS 2 - Benign."
        ),
        "response": (
            "A BI-RADS Category 2 assessment represents benign (non-cancerous) findings with essentially "
            "a 0% risk of malignancy. The ultrasound features described—anechoic (fluid-filled), thin-walled, "
            "well-circumscribed margins with posterior acoustic enhancement—are classic diagnostic hallmarks of "
            "a simple cyst. No intervention or biopsy is clinically indicated for an asymptomatic simple cyst; "
            "the patient should continue routine screening mammography. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "birads_3",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": "What follow-up is recommended when a mammography finding is classified as BI-RADS Category 3?",
        "context": (
            "Left breast diagnostic mammogram: Solitary cluster of round, punctate microcalcifications in "
            "lower inner quadrant. Assessment: BI-RADS 3 - Probably Benign."
        ),
        "response": (
            "A BI-RADS Category 3 assessment represents a 'probably benign' finding with a malignancy risk "
            "greater than 0% but less than or equal to 2%. Because the risk of malignancy is very low, tissue "
            "biopsy is generally avoided to prevent unnecessary procedures. The standard clinical recommendation "
            "is a short-interval follow-up imaging examination (typically at 6 months) of the affected breast "
            "to assess stability over a total monitoring period of 24 to 36 months before downgrading to BI-RADS 2. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "birads_4a",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": "What does a BI-RADS 4A subcategory finding indicate regarding malignancy risk and next steps?",
        "context": (
            "Ultrasound Right Breast: 9 mm partially circumscribed, oval hypoechoic mass at 11 o'clock. "
            "Assessment: BI-RADS 4A - Low Suspicion for Malignancy."
        ),
        "response": (
            "A BI-RADS Category 4A assessment indicates a low suspicion for malignancy, with an expected "
            "likelihood of malignancy greater than 2% but less than or equal to 10%. Although the probability of "
            "cancer is low, it exceeds the threshold for surveillance alone. Therefore, tissue sampling via "
            "image-guided core needle biopsy is recommended to obtain a definitive histopathologic evaluation. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "birads_4b",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": "Explain the clinical reasoning for recommending a biopsy for a BI-RADS 4B assessment.",
        "context": (
            "Mammography Left Breast: Indistinct amorphous microcalcifications in upper outer quadrant spanning "
            "14 mm. Assessment: BI-RADS 4B - Moderate Suspicion for Malignancy."
        ),
        "response": (
            "A BI-RADS Category 4B assessment indicates a moderate suspicion for malignancy, associated with "
            "an estimated probability of malignancy between >10% and <=50%. Because this risk is substantial, "
            "diagnostic tissue sampling (stereotactic or ultrasound-guided core needle biopsy) is clinically "
            "indicated. Following biopsy, histological findings must be correlated with imaging features to "
            "ensure concordance. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "birads_4c",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": "What is the expected malignancy risk and workflow for a BI-RADS 4C breast lesion?",
        "context": (
            "Diagnostic Ultrasound Right Breast: Irregular, microlobulated hypoechoic solid mass measuring "
            "1.8 cm at 9 o'clock with mild acoustic shadowing. Assessment: BI-RADS 4C - High Suspicion for Malignancy."
        ),
        "response": (
            "A BI-RADS Category 4C assessment denotes a high suspicion for malignancy, with an estimated cancer "
            "probability ranging from >50% to <95%. The morphological characteristics (irregular shape, "
            "non-circumscribed margins, hypoechoic texture) are concerning. Immediate core needle biopsy is "
            "indicated. If histology returns benign, a close radiologic-pathologic concordance review is required, "
            "and re-biopsy or surgical excision may be considered if discordant. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "birads_5",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": "How is a BI-RADS 5 assessment interpreted and managed in clinical oncology?",
        "context": (
            "Left Breast Mammogram & Ultrasound: Spiculated, hyperdense 2.4 cm mass with pleomorphic "
            "microcalcifications and architectural distortion. Assessment: BI-RADS 5 - Highly Suggestive."
        ),
        "response": (
            "A BI-RADS Category 5 assessment is highly suggestive of malignancy, carrying a >=95% probability "
            "of breast cancer. Classic features include dense spiculated margins, architectural distortion, and "
            "branching microcalcifications. Prompt image-guided core biopsy is strongly recommended. Any benign "
            "biopsy result from a BI-RADS 5 lesion is automatically considered radiologically-pathologically "
            "discordant and typically mandates surgical excision. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "birads_6",
        "category": InstructionCategory.BIRADS_EXPLANATION,
        "instruction": "What does a BI-RADS 6 designation mean on breast imaging performed after a core biopsy?",
        "context": (
            "Breast MRI: Post-biopsy imaging for extent of disease. Enhancing 2.1 cm mass at prior biopsy site "
            "with biopsy clip in place. Assessment: BI-RADS 6 - Known Biopsy-Proven Malignancy."
        ),
        "response": (
            "A BI-RADS Category 6 designation is reserved for lesions that have already been confirmed as malignant "
            "by prior histopathologic biopsy, before definitive surgical excision or neoadjuvant therapy. Imaging in "
            "this setting is performed for staging, assessing disease extent, evaluating contralateral breast tissue, "
            "or monitoring response to neoadjuvant systemic therapy. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
]

_TNM_TEMPLATES = [
    {
        "id_prefix": "tnm_pt1c_n0_m0",
        "category": InstructionCategory.TNM_REASONING,
        "instruction": (
            "Explain the anatomical extent represented by the pathological stage pT1c pN0 M0 in invasive breast cancer."
        ),
        "context": (
            "Pathology Summary: Invasive ductal carcinoma of right breast, primary tumor measures 1.6 cm. "
            "Sentinel lymph nodes (0/3 positive). Distant metastasis: None. Pathologic stage: pT1c pN0 M0."
        ),
        "response": (
            "According to the AJCC Cancer Staging Manual (8th Edition), pT1c pN0 M0 corresponds to Stage IA "
            "invasive breast cancer: 1. Primary Tumor (pT1c): The invasive tumor is greater than 1.0 cm but "
            "not more than 2.0 cm in greatest dimension. 2. Regional Lymph Nodes (pN0): Histological examination "
            "of 3 sentinel lymph nodes revealed no regional lymph node metastases. 3. Distant Metastasis (M0): "
            "No clinical or radiographic evidence of distant metastatic spread. This indicates localized, "
            "early-stage disease without nodal dissemination. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "tnm_pt2_pn1a_m0",
        "category": InstructionCategory.TNM_REASONING,
        "instruction": "What does a stage of pT2 pN1a M0 signify regarding tumor size and axillary nodal involvement?",
        "context": (
            "Final Pathology Report: Left breast lumpectomy and sentinel lymph node biopsy. Invasive lobular "
            "carcinoma measuring 3.2 cm. Metastasis in 2 sentinel lymph nodes (largest deposit 4 mm). "
            "Stage: pT2 pN1a M0."
        ),
        "response": (
            "Under AJCC 8th edition staging, pT2 pN1a M0 represents Stage IIB breast cancer: "
            "1. Primary Tumor (pT2): The tumor size is greater than 2.0 cm but not more than 5.0 cm (here, 3.2 cm). "
            "2. Regional Lymph Nodes (pN1a): Metastases are histologically verified in 1 to 3 axillary lymph nodes, "
            "with at least one deposit >2.0 mm (here, 2 nodes positive, largest 4 mm). 3. Distant Metastasis (M0): "
            "No distant metastatic spread is identified. Nodal involvement indicates locoregional spread, which is "
            "a key factor in adjuvant systemic and radiation therapy planning. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "tnm_ptis_dcis",
        "category": InstructionCategory.TNM_REASONING,
        "instruction": "How is pTis defined in a surgical pathology report for ductal carcinoma in situ?",
        "context": (
            "Surgical Pathology: Left breast wire-localized excisional biopsy. Ductal carcinoma in situ (DCIS), "
            "cribriform and solid types with intermediate nuclear grade. No stromal invasion identified. "
            "Stage: pTis pN0."
        ),
        "response": (
            "The designation pTis denotes carcinoma in situ (Stage 0). In ductal carcinoma in situ (DCIS), "
            "malignant epithelial cells are strictly confined within the breast ducts without breaching the "
            "surrounding basement membrane into adjacent breast stroma. Because there is no stromal invasion, "
            "cancer cells do not have access to lymphatic or vascular channels, eliminating the risk of distant "
            "metastatic spread from pure DCIS. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
]

_BIOMARKER_TEMPLATES = [
    {
        "id_prefix": "biomarker_er_pr_her2_ki67",
        "category": InstructionCategory.BIOMARKER_ANALYSIS,
        "instruction": (
            "Analyze the biomarker profile: ER 95% strong, PR 80% moderate, HER2 1+, Ki-67 12%. "
            "What breast cancer surrogate subtype does this reflect?"
        ),
        "context": (
            "Immunohistochemistry Report: Estrogen Receptor (ER): Positive (95% nuclear staining, strong intensity). "
            "Progesterone Receptor (PR): Positive (80% nuclear staining, moderate intensity). HER2: Negative (score 1+ "
            "by IHC). Ki-67 proliferation index: 12%."
        ),
        "response": (
            "The reported biomarker panel is consistent with a Luminal A-like breast cancer surrogate subtype: "
            "1. Estrogen Receptor (ER) and Progesterone Receptor (PR) are both strongly positive, indicating tumor "
            "growth is heavily dependent on hormone signaling. 2. HER2 is negative (IHC score 1+), meaning no HER2 "
            "protein overexpression is present, and reflex FISH testing is not required. 3. Ki-67 is low at 12% "
            "(<14–20% threshold), reflecting low proliferative activity. Patients with Luminal A-like profiles "
            "generally have favorable prognostic characteristics and are candidates for endocrine (hormone) therapy. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "biomarker_triple_negative",
        "category": InstructionCategory.BIOMARKER_ANALYSIS,
        "instruction": (
            "What are the therapeutic implications of a Triple-Negative biomarker profile "
            "(ER 0%, PR 0%, HER2 0, Ki-67 75%)?"
        ),
        "context": (
            "Biomarker Analysis: ER: Negative (0%). PR: Negative (0%). HER2: Negative (IHC score 0). "
            "Ki-67 proliferation index: 75% (high)."
        ),
        "response": (
            "This profile demonstrates Triple-Negative Breast Cancer (TNBC): 1. Hormone Receptors (ER and PR) "
            "are negative (<1% staining), meaning endocrine therapies (such as tamoxifen or aromatase inhibitors) "
            "are ineffective. 2. HER2 is negative (IHC score 0), precluding targeted anti-HER2 therapies (such as "
            "trastuzumab). 3. Ki-67 is markedly elevated (75%), indicating rapid tumor cell proliferation. Systemic "
            "treatment for TNBC relies primarily on cytotoxic chemotherapy, potentially combined with immunotherapy "
            "(e.g., pembrolizumab) depending on PD-L1 status and stage. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "biomarker_her2_equivocal_fish",
        "category": InstructionCategory.BIOMARKER_ANALYSIS,
        "instruction": (
            "Explain the necessary reflex testing when HER2 immunohistochemistry returns an equivocal 2+ score."
        ),
        "context": (
            "Pathology Addendum: Right breast invasive ductal carcinoma. "
            "HER2 IHC: Equivocal (score 2+, circumferential membrane staining). "
            "Reflex fluorescence in situ hybridization (FISH) pending."
        ),
        "response": (
            "Under ASCO/CAP guidelines, a HER2 immunohistochemistry (IHC) score of 2+ is considered equivocal. "
            "It cannot determine whether HER2 is positive or negative on protein staining alone. Therefore, reflex "
            "gene amplification testing—typically via Fluorescence In Situ Hybridization (FISH)—is mandatory. If the "
            "FISH HER2/CEP17 ratio is >=2.0 or the average HER2 copy number is >=6.0 signals/cell, the tumor is "
            "classified as HER2-positive. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
]

_SAFETY_REFUSAL_TEMPLATES = [
    {
        "id_prefix": "safety_diagnose_me",
        "category": InstructionCategory.SAFETY_REFUSAL,
        "instruction": "Can you give me a diagnosis and tell me if I definitely have cancer based on this mammogram?",
        "context": (
            "Report snippet: Irregular dense mass measuring 2.1 cm with microlobulated borders in right upper "
            "outer quadrant. BI-RADS 4C."
        ),
        "response": (
            "I cannot provide a medical diagnosis or state definitively whether you have cancer. As an assistive "
            "clinical tool, I can only explain what is documented in your report. Your report describes an irregular "
            "2.1 cm mass categorized as BI-RADS 4C, which indicates a high suspicion for malignancy. However, an "
            "imaging assessment is not a conclusive diagnosis—a tissue biopsy analyzed by a pathologist is necessary "
            "to determine the precise nature of the lesion. Please consult directly with your doctor or breast care "
            "team to discuss these findings and recommended next steps. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "safety_prescribe_chemo",
        "category": InstructionCategory.SAFETY_REFUSAL,
        "instruction": (
            "What chemotherapy prescription should I begin taking tomorrow for my Stage II invasive ductal carcinoma?"
        ),
        "context": "Pathology: Invasive ductal carcinoma, pT2 pN0 M0, ER 90%, PR 85%, HER2 negative.",
        "response": (
            "I cannot prescribe medications, order chemotherapy regimens, or formulate individual clinical treatment "
            "plans. Treatment regimens in breast oncology depend on detailed patient-specific evaluations, including "
            "genomic assays (e.g., Oncotype DX), cardiac evaluation, performance status, and multidisciplinary tumor "
            "board review. You must discuss systemic therapy options directly with your medical oncologist. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "safety_confirm_benign",
        "category": InstructionCategory.SAFETY_REFUSAL,
        "instruction": "Can you confirm my breast lump is completely benign so I can safely skip the biopsy?",
        "context": "Ultrasound: Hypoechoic mass with angular margins at 1 o'clock. BI-RADS 4A. Biopsy recommended.",
        "response": (
            "I cannot confirm that a breast lump is benign, and you should never skip a recommended clinical "
            "biopsy based on AI output. Your ultrasound was classified as BI-RADS 4A, which carries a low but real "
            "probability of malignancy (>2% to 10%). A biopsy is recommended precisely because imaging alone cannot "
            "rule out cancer with certainty. Only a pathologist examining actual tissue cells can determine whether "
            "the lesion is benign. Please follow up promptly with your physician regarding the recommended procedure. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        ),
    },
]

_PATIENT_SUMMARY_TEMPLATES = [
    {
        "id_prefix": "patient_summary_birads_3",
        "category": InstructionCategory.PATIENT_SUMMARY,
        "instruction": (
            "Generate a clinician-reviewed, plain-language patient summary for a report with a BI-RADS 3 finding."
        ),
        "context": (
            "Mammography: Dense breast tissue. Small cluster of rounded calcifications in right breast. "
            "BI-RADS 3: Probably benign. Recommend 6-month follow-up."
        ),
        "response": (
            "Summary of Your Breast Imaging Results:\n\n"
            "• What was found: The mammogram showed dense breast tissue and a small group of rounded calcium deposits "
            "(calcifications) in the right breast.\n"
            "• What this means: The radiologist classified this as BI-RADS 3 ('probably benign'). This means the "
            "finding has a more than 98% chance of being harmless.\n"
            "• Recommended next step: Rather than performing a biopsy, the recommended approach is a short-interval "
            "checkup in 6 months to take another picture and confirm that nothing has changed.\n\n"
            f"{ASSISTIVE_DISCLAIMER}"
        ),
    },
    {
        "id_prefix": "patient_summary_early_stage",
        "category": InstructionCategory.PATIENT_SUMMARY,
        "instruction": (
            "Generate an accessible summary for a patient whose pathology report shows pT1c N0 invasive carcinoma, "
            "ER/PR positive, HER2 negative."
        ),
        "context": (
            "Pathology: Invasive ductal carcinoma, 1.4 cm, negative margins, 0/2 sentinel nodes positive. "
            "ER positive 90%, PR positive 80%, HER2 negative (1+). Stage pT1c N0 M0."
        ),
        "response": (
            "Summary of Your Surgical Pathology Findings:\n\n"
            "• Tumor size: The tumor measured 1.4 centimeters (about the size of a pea or dime) and was removed with "
            "clear margins (no cancer cells seen at the outer edges of the removed tissue).\n"
            "• Lymph nodes: Two sentinel lymph nodes were checked and both were negative for cancer, meaning the "
            "cancer had not spread to the underarm nodes.\n"
            "• Receptor status: The tumor cells tested positive for estrogen and progesterone receptors, and negative "
            "for HER2. This is a common and treatable subtype where hormone therapies are typically very effective.\n"
            "• Next steps: Your oncology care team will review these results with you to discuss follow-up options, "
            "which may include hormone therapy and radiation.\n\n"
            f"{ASSISTIVE_DISCLAIMER}"
        ),
    },
]


def generate_instruction_samples() -> list[InstructionSample]:
    """Generate all curated oncology instruction tuning samples.

    Returns:
        List of validated InstructionSample instances.
    """
    all_raw: list[dict[str, Any]] = [
        *_BIRADS_TEMPLATES,
        *_TNM_TEMPLATES,
        *_BIOMARKER_TEMPLATES,
        *_SAFETY_REFUSAL_TEMPLATES,
        *_PATIENT_SUMMARY_TEMPLATES,
    ]

    samples: list[InstructionSample] = []
    for item in all_raw:
        sample = InstructionSample(
            id=item["id_prefix"],
            category=item["category"],
            instruction=item["instruction"],
            input_context=item.get("context", ""),
            response=item["response"],
            metadata={"source": "aviothic_oncology_guidelines_v1"},
        )
        samples.append(sample)

    return samples


def create_dataset_splits(
    samples: list[InstructionSample],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> DatasetSplit:
    """Split instruction samples into train, validation, and test partitions.

    Deterministic split based on sample IDs and seed.

    Args:
        samples: List of instruction samples.
        train_ratio: Proportion allocated to training.
        val_ratio: Proportion allocated to validation.
        seed: Random seed for reproducibility.

    Returns:
        DatasetSplit containing train, val, and test lists.
    """
    import random

    rng = random.Random(seed)  # noqa: S311
    shuffled = list(samples)
    rng.shuffle(shuffled)

    n_total = len(shuffled)
    n_train = max(1, int(n_total * train_ratio))
    n_val = max(1, int(n_total * val_ratio))

    train = shuffled[:n_train]
    val = shuffled[n_train : n_train + n_val]
    test = shuffled[n_train + n_val :]

    # Ensure test is non-empty if total > 2
    if not test and len(train) > 1:
        test = [train.pop()]

    return DatasetSplit(train=train, val=val, test=test)


def export_dataset_jsonl(samples: list[InstructionSample], output_path: Path) -> int:
    """Export instruction samples to a JSON Lines (JSONL) file.

    Args:
        samples: Samples to export.
        output_path: Target file path.

    Returns:
        Number of written lines.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.model_dump(), ensure_ascii=False) + "\n")
    return len(samples)
