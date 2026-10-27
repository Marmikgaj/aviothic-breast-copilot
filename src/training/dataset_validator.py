"""Dataset validation and de-identification engine for oncology instruction data.

Enforces:
1. Zero Protected Health Information (PHI) leakage (SSN, MRN, phone, email, names).
2. Zero diagnostic assertions (Rules.md §8).
3. Mandatory assistive disclaimers on patient explanations.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from src.training.schemas import InstructionCategory, InstructionSample

# Regex patterns for accidental PHI leakage detection.
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_MRN_PATTERN = re.compile(r"\b(?:MRN|Medical Record No|Patient ID|Acct #)[:\s]*\d{5,}\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PATIENT_NAME_LABEL_PATTERN = re.compile(
    r"\b(?:Patient(?:\s+Name)?|Pt\.?\s+Name)\s*:\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+",
    re.IGNORECASE,
)

# Forbidden diagnostic claims that violate Rules.md §8.
_FORBIDDEN_DIAGNOSTIC_PATTERNS = [
    re.compile(r"\b(?:I\s+diagnose\s+you\s+with)\b", re.IGNORECASE),
    re.compile(r"\b(?:you\s+definitely\s+have\s+cancer)\b", re.IGNORECASE),
    re.compile(r"\b(?:this\s+(?:definitively|conclusively)\s+proves\s+malignancy)\b", re.IGNORECASE),
    re.compile(r"\b(?:this\s+confirms\s+you\s+have\s+breast\s+cancer)\b", re.IGNORECASE),
    re.compile(r"\b(?:this\s+is\s+100%\s+(?:benign|malignant))\b", re.IGNORECASE),
    re.compile(r"\b(?:I\s+(?:prescribe|order)\s+you\s+to\s+take)\b", re.IGNORECASE),
]

_DISCLAIMER_KEYWORDS = ["assistive", "not a medical diagnosis", "doctor", "care team", "oncologist", "consult"]


@dataclass
class ValidationIssue:
    """Represents a specific validation finding on an instruction sample."""

    sample_id: str
    issue_type: str
    message: str
    snippet: str = ""


@dataclass
class DatasetValidationReport:
    """Summary report of dataset validation."""

    total_checked: int
    is_valid: bool
    phi_violations: int = 0
    diagnostic_violations: int = 0
    missing_disclaimers: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)


def check_for_phi(text: str) -> list[tuple[str, str]]:
    """Scan text for potential Protected Health Information (PHI).

    Returns:
        List of tuples: (pattern_name, matching_snippet).
    """
    matches: list[tuple[str, str]] = []
    for name, pattern in (
        ("SSN", _SSN_PATTERN),
        ("MRN", _MRN_PATTERN),
        ("Phone", _PHONE_PATTERN),
        ("Email", _EMAIL_PATTERN),
        ("Patient Name", _PATIENT_NAME_LABEL_PATTERN),
    ):
        match = pattern.search(text)
        if match:
            matches.append((name, match.group(0)))
    return matches


def check_for_diagnostic_assertion(text: str) -> str | None:
    """Check if text contains forbidden definitive diagnostic assertions.

    Returns:
        The matched forbidden phrase if found, or None.
    """
    for pattern in _FORBIDDEN_DIAGNOSTIC_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def has_assistive_disclaimer(text: str) -> bool:
    """Verify that text contains acceptable assistive framing/disclaimer."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in _DISCLAIMER_KEYWORDS)


def validate_instruction_sample(sample: InstructionSample) -> list[ValidationIssue]:
    """Validate a single instruction sample for PHI, safety, and disclaimers.

    Args:
        sample: InstructionSample to validate.

    Returns:
        List of ValidationIssues (empty if sample is clean).
    """
    issues: list[ValidationIssue] = []

    # 1. PHI Check across all text fields
    full_text = f"{sample.instruction} {sample.input_context} {sample.response}"
    phi_findings = check_for_phi(full_text)
    for p_name, p_snippet in phi_findings:
        issues.append(
            ValidationIssue(
                sample_id=sample.id,
                issue_type="PHI_DETECTED",
                message=f"Potential {p_name} detected in sample.",
                snippet=p_snippet,
            )
        )

    # 2. Diagnostic Assertion Check
    diag_snippet = check_for_diagnostic_assertion(sample.response)
    if diag_snippet:
        issues.append(
            ValidationIssue(
                sample_id=sample.id,
                issue_type="DIAGNOSTIC_ASSERTION",
                message="Forbidden definitive diagnostic claim found in response.",
                snippet=diag_snippet,
            )
        )

    # 3. Patient Summary / Refusal Disclaimer Check
    if sample.category in (InstructionCategory.PATIENT_SUMMARY, InstructionCategory.SAFETY_REFUSAL):
        if not has_assistive_disclaimer(sample.response):
            issues.append(
                ValidationIssue(
                    sample_id=sample.id,
                    issue_type="MISSING_DISCLAIMER",
                    message="Patient summary or safety refusal lacks mandatory clinical disclaimer.",
                    snippet=sample.response[:100],
                )
            )

    return issues


def validate_dataset(samples: Sequence[InstructionSample]) -> DatasetValidationReport:
    """Validate an entire collection of instruction samples.

    Args:
        samples: Sequence of InstructionSample objects.

    Returns:
        DatasetValidationReport summarizing pass/fail status and all issues.
    """
    total = len(samples)
    all_issues: list[ValidationIssue] = []
    phi_count = 0
    diag_count = 0
    disclaimer_count = 0

    for sample in samples:
        sample_issues = validate_instruction_sample(sample)
        for issue in sample_issues:
            all_issues.append(issue)
            if issue.issue_type == "PHI_DETECTED":
                phi_count += 1
            elif issue.issue_type == "DIAGNOSTIC_ASSERTION":
                diag_count += 1
            elif issue.issue_type == "MISSING_DISCLAIMER":
                disclaimer_count += 1

    is_valid = len(all_issues) == 0
    return DatasetValidationReport(
        total_checked=total,
        is_valid=is_valid,
        phi_violations=phi_count,
        diagnostic_violations=diag_count,
        missing_disclaimers=disclaimer_count,
        issues=all_issues,
    )
