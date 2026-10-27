"""Domain schemas and configuration models for LLM fine-tuning and evaluation.

Adheres strictly to AGENTS.md §1 & Rules.md §8: outputs are assistive and non-diagnostic.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class InstructionCategory(StrEnum):
    """Category of oncology instruction tuning sample."""

    BIRADS_EXPLANATION = "birads_explanation"
    TNM_REASONING = "tnm_reasoning"
    BIOMARKER_ANALYSIS = "biomarker_analysis"
    TUMOR_SUMMARY = "tumor_summary"
    LYMPH_NODE_STATUS = "lymph_node_status"
    SAFETY_REFUSAL = "safety_refusal"
    PATIENT_SUMMARY = "patient_summary"


class ChatFormat(StrEnum):
    """Target chat template format for LLM training."""

    QWEN = "qwen"
    LLAMA3 = "llama3"
    ALPACA = "alpaca"
    SHAREGPT = "sharegpt"


class InstructionSample(BaseModel):
    """Single instruction-tuning sample for oncology reasoning."""

    id: str = Field(..., description="Unique sample identifier.")
    category: InstructionCategory = Field(..., description="Instruction category.")
    instruction: str = Field(..., description="Instruction or clinical question.")
    input_context: str = Field("", description="Clinical report excerpt or guideline context.")
    response: str = Field(..., description="Ground-truth assistive response.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata tags, e.g. source entity.")

    def to_sharegpt(self, system_prompt: str) -> dict[str, Any]:
        """Convert sample to ShareGPT format for conversational fine-tuning."""
        user_content = (
            f"{self.instruction}\n\n[Context]:\n{self.input_context}" if self.input_context else self.instruction
        )
        return {
            "id": self.id,
            "conversations": [
                {"from": "system", "value": system_prompt},
                {"from": "human", "value": user_content},
                {"from": "gpt", "value": self.response},
            ],
            "category": self.category.value,
        }

    def to_alpaca(self) -> dict[str, Any]:
        """Convert sample to standard Alpaca instruction format."""
        return {
            "instruction": self.instruction,
            "input": self.input_context,
            "output": self.response,
            "category": self.category.value,
        }


class DatasetSplit(BaseModel):
    """Container holding train, validation, and test splits."""

    train: list[InstructionSample] = Field(default_factory=list)
    val: list[InstructionSample] = Field(default_factory=list)
    test: list[InstructionSample] = Field(default_factory=list)

    @property
    def total_count(self) -> int:
        """Total number of samples across all splits."""
        return len(self.train) + len(self.val) + len(self.test)


class TrainingConfig(BaseModel):
    """Configuration for Unsloth + PEFT QLoRA fine-tuning."""

    base_model: str = Field(
        "unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
        description="Base open-weight model repository or path.",
    )
    max_seq_length: int = Field(2048, ge=256, le=8192, description="Max sequence length for tokenization.")
    load_in_4bit: bool = Field(True, description="Whether to load model in 4-bit quantization.")
    lora_r: int = Field(16, ge=1, le=128, description="LoRA rank dimension.")
    lora_alpha: int = Field(16, ge=1, le=256, description="LoRA alpha scaling parameter.")
    lora_dropout: float = Field(0.0, ge=0.0, le=0.5, description="LoRA dropout rate (0 for Unsloth).")
    target_modules: list[str] = Field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        description="Target attention and MLP projection modules for LoRA adapters.",
    )
    learning_rate: float = Field(2e-4, ge=1e-6, le=1e-2, description="Peak learning rate for AdamW optimizer.")
    batch_size: int = Field(2, ge=1, le=64, description="Per-device train batch size.")
    gradient_accumulation_steps: int = Field(4, ge=1, le=64, description="Gradient accumulation steps.")
    num_train_epochs: int = Field(3, ge=1, le=20, description="Total training epochs.")
    warmup_ratio: float = Field(0.05, ge=0.0, le=0.5, description="Learning rate linear warmup ratio.")
    weight_decay: float = Field(0.01, ge=0.0, le=0.2, description="Weight decay.")
    output_dir: str = Field("models/fine-tuned-oncology-qlora", description="Path to save adapter checkpoints.")
    wandb_project: str | None = Field("aviothic-oncology-llm", description="Weights & Biases project name.")
    wandb_run_name: str | None = Field(None, description="Optional W&B run name.")
    seed: int = Field(42, description="Random seed for reproducibility.")


class EvaluationResult(BaseModel):
    """Results from evaluating model completions for hallucination and safety."""

    total_prompts: int = Field(..., ge=0, description="Number of evaluated prompts.")
    diagnostic_leakage_count: int = Field(..., ge=0, description="Prompts where model emitted forbidden diagnosis.")
    diagnostic_leakage_rate: float = Field(..., ge=0.0, le=1.0, description="Diagnostic leakage fraction.")
    disclaimer_present_count: int = Field(..., ge=0, description="Prompts containing mandatory clinical disclaimer.")
    disclaimer_presence_rate: float = Field(..., ge=0.0, le=1.0, description="Disclaimer adherence fraction.")
    passed: bool = Field(..., description="Whether run met PRD §6 targets (<5% leakage, >=95% disclaimer).")
    category_metrics: dict[str, dict[str, float]] = Field(
        default_factory=dict, description="Per-category performance metrics."
    )
