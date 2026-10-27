"""Clinical safety guardrails and citation enforcement engine.

Strictly enforces:
1. Non-diagnostic policy (Rules.md §8: NEVER state a definitive diagnosis or malignancy).
2. Mandatory clinical assistive disclaimer presence (PRD §4 & §6).
3. Citation enforcement on clinical claims (Architecture §2 & Phases §7).
4. Off-context query boundary enforcement.
5. De-identification / PHI leakage prevention.
"""

from __future__ import annotations

import re

from src.context.schemas import CitationReference, PatientContext
from src.core.logging import get_logger
from src.safety.schemas import SafetyCheckResult
from src.training.dataset_validator import check_for_phi

logger = get_logger(__name__)

MANDATORY_ASSISTIVE_DISCLAIMER = (
    "Note: This information is AI-generated for clinical decision support and educational reference only. "
    "It is not a clinical diagnosis. All findings and management plans must be reviewed and confirmed by "
    "a qualified physician or oncology care team."
)

OFF_CONTEXT_REFUSAL = (
    "I am specialized solely as an assistive breast cancer clinical copilot. I cannot answer questions outside "
    "the scope of breast imaging, pathology, staging, and oncology clinical guidelines. Please consult the "
    "appropriate resources for this topic.\n\n" + MANDATORY_ASSISTIVE_DISCLAIMER
)

# Prohibited definitive diagnostic regex patterns (Rules.md §8)
_DIAGNOSTIC_ASSERTION_PATTERNS = [
    re.compile(r"\b(?:i\s+diagnose\s+(?:you|the\s+patient)\s+with)\b", re.IGNORECASE),
    re.compile(r"\b(?:my\s+(?:definitive\s+)?diagnosis\s+is)\b", re.IGNORECASE),
    re.compile(r"\b(?:you\s+(?:definitely|certainly)\s+have\s+(?:breast\s+)?cancer)\b", re.IGNORECASE),
    re.compile(r"\b(?:this\s+(?:confirms|proves)\s+(?:you\s+have\s+)?malignancy)\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+conclude\s+definitively\s+that\s+you\s+have)\b", re.IGNORECASE),
    re.compile(r"\b(?:guaranteed\s+cure)\b", re.IGNORECASE),
    re.compile(r"\b(?:you\s+do\s+not\s+need\s+(?:a\s+doctor|medical\s+attention))\b", re.IGNORECASE),
]

# Clinical claim keywords that trigger the requirement for citations
_CLINICAL_CLAIM_KEYWORDS = [
    "bi-rads",
    "birads",
    "t1",
    "t2",
    "t3",
    "t4",
    "n0",
    "n1",
    "n2",
    "m0",
    "m1",
    "tnm",
    "stage",
    "her2",
    "estrogen receptor",
    "progesterone receptor",
    "endocrine therapy",
    "tamoxifen",
    "trastuzumab",
    "chemotherapy",
    "biopsy",
    "sentinel",
    "axillary dissection",
    "concordance",
    "discordance",
]

# Off-context topic triggers
_OFF_CONTEXT_PATTERNS = [
    re.compile(
        r"\b(?:write\s+(?:a\s+)?(?:code|python|javascript|script|essay|poem)|stocks?|bitcoin|crypto|weather|legal\s+advice)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:solve\s+math|tell\s+(?:me\s+)?(?:a\s+)?joke|lottery|recipe|horoscope)\b",
        re.IGNORECASE,
    ),
]


class SafetyGuardrail:
    """Enforces non-diagnostic clinical boundaries, mandatory disclaimers, and citation integrity."""

    def is_off_context_query(self, query: str) -> bool:
        """Check if user query is outside the breast oncology domain."""
        clean = query.strip().lower()
        for pattern in _OFF_CONTEXT_PATTERNS:
            if pattern.search(clean):
                return True
        return False

    def check_diagnostic_leakage(self, text: str) -> list[str]:
        """Detect forbidden definitive diagnostic claims violating Rules.md §8."""
        violations: list[str] = []
        for pattern in _DIAGNOSTIC_ASSERTION_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append(f"Diagnostic leakage detected: '{match.group(0)}'")
        return violations

    def has_clinical_claims(self, text: str) -> bool:
        """Check if response asserts clinical findings or therapeutic recommendations."""
        lower_text = text.lower()
        return any(kw in lower_text for kw in _CLINICAL_CLAIM_KEYWORDS)

    def check_citation_presence(self, text: str, citations: list[CitationReference]) -> bool:
        """Verify that citations exist when clinical claims are present."""
        if not self.has_clinical_claims(text):
            return True

        if citations:
            return True

        # Check for inline citation markers (e.g. [1], [Report, [NCCN, [ASCO, [PMID)
        inline_citation_pattern = re.compile(r"\[(?:[0-9]+|Report|NCCN|ASCO|AJCC|ESMO|PMID|Giuliano)[^\]]*\]")
        return bool(inline_citation_pattern.search(text))

    def sanitize_diagnostic_leakage(self, text: str) -> str:
        """Sanitize text by replacing definitive assertions with assistive framing."""
        sanitized = text
        sanitized = re.sub(
            r"\b(?:I\s+diagnose\s+(?:you|the\s+patient)\s+with)\b",
            "The report findings are suspicious for",
            sanitized,
            flags=re.IGNORECASE,
        )
        sanitized = re.sub(
            r"\b(?:You\s+definitely\s+have\s+cancer)\b",
            "The imaging findings warrant histological evaluation",
            sanitized,
            flags=re.IGNORECASE,
        )
        sanitized = re.sub(
            r"\b(?:My\s+diagnosis\s+is)\b",
            "The report impressions indicate",
            sanitized,
            flags=re.IGNORECASE,
        )
        return sanitized

    def ensure_disclaimer(self, text: str) -> str:
        """Ensure the mandatory assistive disclaimer is appended if missing."""
        lower = text.lower()
        disclaimer_markers = [
            "ai-generated for clinical decision support",
            "not a clinical diagnosis",
            "educational reference only",
            "consult with a qualified physician",
            "review and confirmed by a qualified physician",
        ]
        if any(marker in lower for marker in disclaimer_markers):
            return text

        return text.rstrip() + "\n\n" + MANDATORY_ASSISTIVE_DISCLAIMER

    def validate_and_guard(
        self,
        response: str,
        query: str,
        context: PatientContext | None = None,
        citations: list[CitationReference] | None = None,
    ) -> SafetyCheckResult:
        """Validate response against all safety, grounding, and non-diagnostic boundaries.

        Args:
            response: Model-generated response text.
            query: The user's query.
            context: Active patient context.
            citations: Attached grounding citations.

        Returns:
            SafetyCheckResult containing safety flag, violations, and sanitized response.
        """
        citations_list = citations or []
        violations: list[str] = []

        # 1. Check off-context query
        if self.is_off_context_query(query):
            logger.warning("Off-context query detected, issuing standardized refusal", query=query[:80])
            return SafetyCheckResult(
                is_safe=False,
                is_off_context=True,
                violations=["Query is outside breast oncology domain"],
                sanitized_response=OFF_CONTEXT_REFUSAL,
            )

        # 2. Check PHI leakage
        phi_findings = check_for_phi(response)
        if phi_findings:
            violations.extend([f"Potential PHI leakage: {p}" for p in phi_findings])
            logger.error("PHI leakage detected in response", violations=violations)

        # 3. Check diagnostic leakage
        diag_violations = self.check_diagnostic_leakage(response)
        has_diagnostic_leak = len(diag_violations) > 0
        if has_diagnostic_leak:
            violations.extend(diag_violations)
            logger.warning("Diagnostic leakage detected, sanitizing", violations=diag_violations)

        # 4. Check citation requirement
        has_citations = self.check_citation_presence(response, citations_list)
        if not has_citations:
            violations.append("Clinical claims made without verifiable citation attribution")
            logger.warning("Uncited clinical claims detected in response")

        # Sanitize response
        sanitized = self.sanitize_diagnostic_leakage(response)
        sanitized = self.ensure_disclaimer(sanitized)

        # Append bibliography if citations present and not already formatted
        if citations_list and not re.search(r"### References|References:", sanitized, re.IGNORECASE):
            ref_lines = ["\n\n### References & Citations:"]
            for idx, cit in enumerate(citations_list, 1):
                ref_lines.append(f"[{idx}] {cit.source_type.value.upper()}: {cit.source_id} — {cit.text_snippet}")
            sanitized += "\n".join(ref_lines)

        is_safe = len(violations) == 0

        return SafetyCheckResult(
            is_safe=is_safe,
            has_diagnostic_leakage=has_diagnostic_leak,
            has_disclaimer=True,
            has_citations=has_citations,
            is_off_context=False,
            violations=violations,
            sanitized_response=sanitized,
        )
