"""QLoRA fine-tuning execution pipeline using Unsloth and PEFT.

Orchestrates parameter-efficient fine-tuning on Qwen2.5/Llama 3 open-weight models.
Supports single-GPU execution on RunPod/Vast.ai, with dry-run support for CI/CPU testing.
Tracks training metrics in Weights & Biases per ADR-004 and Architecture §2.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.logging import get_logger
from src.training.dataset_generator import create_dataset_splits, generate_instruction_samples
from src.training.dataset_validator import validate_dataset
from src.training.prompt_formatter import format_prompt
from src.training.schemas import ChatFormat, InstructionSample, TrainingConfig

logger = get_logger(__name__)


@dataclass
class TrainingRunResult:
    """Result summary of a QLoRA training run."""

    status: str
    output_dir: str
    train_samples_count: int
    val_samples_count: int
    base_model: str
    lora_rank: int
    epochs: int
    wandb_run_id: str | None = None
    dry_run: bool = False


def check_gpu_environment() -> dict[str, Any]:
    """Inspect environment for GPU and CUDA availability.

    Returns:
        Dictionary with hardware and accelerator metadata.
    """
    env_info: dict[str, Any] = {
        "cuda_available": False,
        "device_name": "CPU",
        "device_count": 0,
        "unsloth_installed": False,
    }

    try:
        import torch

        if torch.cuda.is_available():
            env_info["cuda_available"] = True
            env_info["device_count"] = torch.cuda.device_count()
            env_info["device_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    try:
        import unsloth  # noqa: F401

        env_info["unsloth_installed"] = True
    except ImportError:
        pass

    return env_info


def prepare_training_dataset(
    samples: list[InstructionSample],
    chat_format: ChatFormat = ChatFormat.QWEN,
) -> list[dict[str, Any]]:
    """Format instruction samples into training records for SFTTrainer.

    Args:
        samples: List of raw InstructionSample objects.
        chat_format: Target template format.

    Returns:
        List of formatted dictionary records with 'text'.
    """
    formatted_data: list[dict[str, Any]] = []
    for sample in samples:
        text = format_prompt(sample, format_type=chat_format)
        if isinstance(text, str):
            formatted_data.append({"text": text, "category": sample.category.value, "id": sample.id})
        elif isinstance(text, dict):
            formatted_data.append(text)
    return formatted_data


def run_qlora_training(
    config: TrainingConfig,
    samples: list[InstructionSample] | None = None,
    dry_run: bool = False,
) -> TrainingRunResult:
    """Execute QLoRA fine-tuning run.

    In production/GPU environment:
        Loads base model via Unsloth/PEFT with 4-bit quantization, configures LoRA,
        initializes SFTTrainer, logs to Weights & Biases, and saves adapter weights.

    In dry-run / CPU environment:
        Validates configuration, verifies dataset integrity and de-identification,
        simulates tokenization formatting, and outputs checkpoint metadata.

    Args:
        config: Training configuration settings.
        samples: Optional list of instruction samples. If None, generated automatically.
        dry_run: If True, executes pipeline validation without launching heavy GPU training.

    Returns:
        TrainingRunResult containing run status and artifacts.
    """
    logger.info("Initializing QLoRA fine-tuning pipeline", base_model=config.base_model, dry_run=dry_run)

    # 1. Prepare and validate instruction dataset
    if samples is None:
        samples = generate_instruction_samples()

    validation_report = validate_dataset(samples)
    if not validation_report.is_valid:
        raise ValueError(f"Dataset validation failed with {len(validation_report.issues)} safety/PHI issues.")

    splits = create_dataset_splits(samples, seed=config.seed)
    logger.info(
        "Dataset splits prepared",
        train_count=len(splits.train),
        val_count=len(splits.val),
        test_count=len(splits.test),
    )

    env_info = check_gpu_environment()
    logger.info("Hardware environment checked", **env_info)

    # Dry-run or non-GPU fallback
    if dry_run or not env_info["cuda_available"] or not env_info["unsloth_installed"]:
        reason = "dry_run flag requested" if dry_run else "CUDA or unsloth unavailable (running in CPU/CI mode)"
        logger.info(f"Executing training pipeline verification ({reason})")

        train_records = prepare_training_dataset(splits.train, chat_format=ChatFormat.QWEN)
        val_records = prepare_training_dataset(splits.val, chat_format=ChatFormat.QWEN)

        output_path = Path(config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        summary_file = output_path / "training_summary.json"
        summary_data = {
            "status": "completed_verification",
            "dry_run": True,
            "base_model": config.base_model,
            "lora_rank": config.lora_r,
            "lora_alpha": config.lora_alpha,
            "epochs": config.num_train_epochs,
            "train_samples": len(train_records),
            "val_samples": len(val_records),
            "output_dir": str(output_path),
            "hardware": env_info,
        }
        with summary_file.open("w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        logger.info("Training pipeline verification completed successfully", output_file=str(summary_file))
        return TrainingRunResult(
            status="verified",
            output_dir=str(output_path),
            train_samples_count=len(train_records),
            val_samples_count=len(val_records),
            base_model=config.base_model,
            lora_rank=config.lora_r,
            epochs=config.num_train_epochs,
            dry_run=True,
        )

    # Production GPU execution using Unsloth
    logger.info("Launching Unsloth FastLanguageModel training on GPU...")
    try:
        from datasets import Dataset
        from transformers import TrainingArguments
        from trl import SFTTrainer
        from unsloth import FastLanguageModel

        if config.wandb_project and "WANDB_API_KEY" in os.environ:
            import wandb

            wandb.init(project=config.wandb_project, name=config.wandb_run_name, config=config.model_dump())

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=config.base_model,
            max_seq_length=config.max_seq_length,
            load_in_4bit=config.load_in_4bit,
        )

        model = FastLanguageModel.get_peft_model(
            model,
            r=config.lora_r,
            target_modules=config.target_modules,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=config.seed,
        )

        train_records = prepare_training_dataset(splits.train)
        val_records = prepare_training_dataset(splits.val)
        train_ds = Dataset.from_list(train_records)
        val_ds = Dataset.from_list(val_records)

        training_args = TrainingArguments(
            per_device_train_batch_size=config.batch_size,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
            warmup_ratio=config.warmup_ratio,
            num_train_epochs=config.num_train_epochs,
            learning_rate=config.learning_rate,
            fp16=True,
            logging_steps=1,
            output_dir=config.output_dir,
            seed=config.seed,
            weight_decay=config.weight_decay,
            report_to="wandb" if config.wandb_project else "none",
        )

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            dataset_text_field="text",
            max_seq_length=config.max_seq_length,
            args=training_args,
        )

        trainer.train()
        model.save_pretrained(config.output_dir)
        tokenizer.save_pretrained(config.output_dir)

        logger.info("QLoRA training successfully completed and adapters saved", output_dir=config.output_dir)
        return TrainingRunResult(
            status="completed",
            output_dir=config.output_dir,
            train_samples_count=len(train_records),
            val_samples_count=len(val_records),
            base_model=config.base_model,
            lora_rank=config.lora_r,
            epochs=config.num_train_epochs,
            dry_run=False,
        )
    except Exception as exc:
        logger.exception("GPU training failed with error", error=str(exc))
        raise


def main() -> None:
    """CLI entrypoint for running QLoRA training."""
    parser = argparse.ArgumentParser(description="Aviothic Oncology LLM QLoRA Fine-Tuning Pipeline")
    parser.add_argument("--base-model", type=str, default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
    parser.add_argument("--output-dir", type=str, default="models/fine-tuned-oncology-qlora")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--dry-run", action="store_true", help="Run verification without launching full GPU training")

    args = parser.parse_args()

    cfg = TrainingConfig(
        base_model=args.base_model,
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        batch_size=args.batch_size,
        lora_r=args.lora_r,
        learning_rate=args.learning_rate,
    )

    result = run_qlora_training(cfg, dry_run=args.dry_run)
    logger.info("Run finished", status=result.status, output_dir=result.output_dir)


if __name__ == "__main__":
    main()
