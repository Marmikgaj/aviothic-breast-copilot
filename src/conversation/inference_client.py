"""Inference client abstraction supporting vLLM endpoints and deterministic offline execution.

Complies with Architecture §6 (Open-weight LLM served via vLLM with fallback for local testing).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class BaseInferenceClient(ABC):
    """Abstract interface for LLM text generation."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate response text for the given prompt.

        Args:
            prompt: User or assembled prompt text.
            system_prompt: Optional system framing prompt.

        Returns:
            Generated completion string.
        """
        ...


class VLLMInferenceClient(BaseInferenceClient):
    """HTTP client for vLLM or OpenAI-compatible completion server."""

    def __init__(
        self,
        api_base: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        fallback_client: BaseInferenceClient | None = None,
    ) -> None:
        settings = get_settings()
        self.api_base = (api_base or settings.llm_api_base).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout = timeout or settings.llm_request_timeout
        self.fallback_client = fallback_client

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        endpoint = f"{self.api_base}/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        settings = get_settings()
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_new_tokens,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                result: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                choice = result.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                return str(content).strip()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.warning("vLLM server unreachable, falling back to local reasoning engine", error=str(e))
            if self.fallback_client:
                return self.fallback_client.generate(prompt, system_prompt)
            raise RuntimeError(f"Failed to communicate with inference server at {endpoint}: {e}") from e


class MockInferenceClient(BaseInferenceClient):
    """Deterministic reasoning engine for offline development, CI, and test execution."""

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Produce clinically structured assistive reasoning based on prompt contents."""
        lower = prompt.lower()

        # Handle report comparison queries
        if "compare" in lower or "concordance" in lower or "correlation" in lower:
            return (
                "Based on the cross-report findings in this patient session:\n\n"
                "• Imaging & Histology Correlation: The imaging findings correlate with subsequent tissue sampling. "
                "The documented tumor characteristics, margins, and receptor statuses align with established "
                "pathology criteria [1].\n"
                "• Trajectory Assessment: The patient's evaluation progressed from initial diagnostic imaging to "
                "definitive histopathological evaluation.\n\n"
                "Recommendation: Multidisciplinary tumor board discussion is advised to correlate tumor staging with "
                "planned systemic and locoregional therapies."
            )

        # Handle BI-RADS queries
        if "bi-rads" in lower or "birads" in lower:
            category = "4C" if "4c" in lower else "4" if "4" in lower else "3" if "3" in lower else "5"
            return (
                f"Regarding the BI-RADS Category {category} assessment:\n\n"
                f"• Clinical Significance: BI-RADS Category {category} indicates findings with sufficient suspicion to "
                "warrant tissue biopsy rather than routine screening [1].\n"
                "• Recommended Next Steps: Per NCCN and ACR screening guidelines, image-guided core needle biopsy "
                "is indicated to establish definitive histological diagnosis [1].\n"
                "• Action Plan: Correlation with prior mammographic films and subsequent pathology results "
                "is necessary."
            )

        # Handle TNM / Staging queries
        if "tnm" in lower or "stage" in lower or "pt1" in lower:
            return (
                "Based on the documented AJCC 8th Edition pathological staging:\n\n"
                "• Anatomical Extent: The primary tumor dimension corresponds to early-stage invasive breast "
                "carcinoma [1].\n"
                "• Nodal & Distant Status: Regional lymph node status and distant metastasis parameters define "
                "the overall prognostic stage group [1].\n"
                "• Clinical Guidance: Pathological staging dictates the necessity and sequence of adjuvant or "
                "neoadjuvant systemic therapy."
            )

        # Handle Biomarker queries
        if "her2" in lower or "er" in lower or "pr" in lower or "receptor" in lower:
            return (
                "Regarding the hormone receptor and HER2 biomarker profile:\n\n"
                "• Estrogen / Progesterone Status: Positive hormone receptor status confers favorable responsiveness "
                "to endocrine therapy such as aromatase inhibitors or tamoxifen [1].\n"
                "• HER2 Expression: HER2 status directs eligibility for targeted anti-HER2 monoclonal antibody "
                "regimens [1].\n"
                "• Overall Subtype: Biomarker combinations define the surrogate intrinsic molecular subtype guiding "
                "systemic treatment selection."
            )

        # Generic grounded clinical response
        return (
            "Based on the available clinical documentation and oncology guidelines [1]:\n\n"
            "The report outlines findings requiring integrated radiological and pathological assessment. "
            "Grounded clinical guidelines emphasize multidisciplinary evaluation and appropriate follow-up imaging."
        )


def get_inference_client() -> BaseInferenceClient:
    """Return configured inference client with fallback."""
    settings = get_settings()
    mock_client = MockInferenceClient()
    if settings.llm_mock_fallback:
        return VLLMInferenceClient(
            api_base=settings.llm_api_base,
            model=settings.llm_model,
            timeout=settings.llm_request_timeout,
            fallback_client=mock_client,
        )
    return VLLMInferenceClient(
        api_base=settings.llm_api_base,
        model=settings.llm_model,
        timeout=settings.llm_request_timeout,
    )
