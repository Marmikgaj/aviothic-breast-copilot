"""Prompt formatter for target LLM chat templates and system instructions.

Enforces system-level non-diagnostic framing and consistent chat markup for Qwen & Llama 3.
Adheres strictly to ADR-004, ADR-006, and Rules.md §8.
"""

from __future__ import annotations

from typing import Any

from src.training.schemas import ChatFormat, InstructionSample

SYSTEM_PROMPT = (
    "You are the Aviothic Clinical AI Copilot, an assistive reasoning assistant for breast oncology reports. "
    "You organize and explain clinical facts present in provided clinical reports and oncology guidelines. "
    "You NEVER provide a definitive clinical diagnosis or malignancy determination. "
    "All outputs are assistive and non-diagnostic; always recommend consultation with a qualified oncologist "
    "or multidisciplinary breast care team."
)

ASSISTIVE_DISCLAIMER = (
    "Note: This is an assistive clinical explanation based on provided report findings, not a medical diagnosis. "
    "Treatment choices and clinical staging must be determined in consultation with your oncologist and care team."
)


def format_messages(sample: InstructionSample, system_prompt: str = SYSTEM_PROMPT) -> list[dict[str, str]]:
    """Format sample into a standard conversational messages list.

    Args:
        sample: Instruction sample to format.
        system_prompt: System prompt override.

    Returns:
        List of message dicts with 'role' and 'content'.
    """
    user_content = (
        f"{sample.instruction}\n\n[Clinical Context]:\n{sample.input_context}"
        if sample.input_context
        else sample.instruction
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": sample.response},
    ]


def format_qwen(sample: InstructionSample, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Format sample into Qwen ChatML string format."""
    messages = format_messages(sample, system_prompt)
    output: list[str] = []
    for msg in messages:
        output.append(f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>")
    return "\n".join(output) + "\n"


def format_llama3(sample: InstructionSample, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Format sample into Llama 3 chat template string format."""
    messages = format_messages(sample, system_prompt)
    output: list[str] = ["<|begin_of_text|>"]
    for msg in messages:
        output.append(f"<|start_header_id|>{msg['role']}<|end_header_id|>\n\n" f"{msg['content']}<|eot_id|>")
    return "\n".join(output) + "\n"


def format_prompt(
    sample: InstructionSample,
    format_type: ChatFormat = ChatFormat.QWEN,
    system_prompt: str = SYSTEM_PROMPT,
) -> Any:
    """Format an instruction sample into the specified chat or training format.

    Args:
        sample: The instruction sample.
        format_type: Target output format.
        system_prompt: System prompt instructing the model.

    Returns:
        Formatted string or dictionary suitable for model fine-tuning.
    """
    if format_type == ChatFormat.QWEN:
        return format_qwen(sample, system_prompt)
    if format_type == ChatFormat.LLAMA3:
        return format_llama3(sample, system_prompt)
    if format_type == ChatFormat.ALPACA:
        return sample.to_alpaca()
    if format_type == ChatFormat.SHAREGPT:
        return sample.to_sharegpt(system_prompt)
    raise ValueError(f"Unsupported format type: {format_type}")
