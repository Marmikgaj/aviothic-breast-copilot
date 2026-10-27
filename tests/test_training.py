"""Tests for Phase 4 Oncology LLM fine-tuning, dataset curation, and evaluation pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.training.dataset_generator import (
    create_dataset_splits,
    export_dataset_jsonl,
    generate_instruction_samples,
)
from src.training.dataset_validator import (
    check_for_diagnostic_assertion,
    check_for_phi,
    has_assistive_disclaimer,
    validate_dataset,
    validate_instruction_sample,
)
from src.training.evaluator import (
    HELD_OUT_EVAL_CASES,
    evaluate_completion,
    evaluate_model,
)
from src.training.prompt_formatter import (
    ASSISTIVE_DISCLAIMER,
    SYSTEM_PROMPT,
    format_llama3,
    format_prompt,
    format_qwen,
)
from src.training.schemas import (
    ChatFormat,
    InstructionCategory,
    InstructionSample,
    TrainingConfig,
)
from src.training.train_qlora import check_gpu_environment, run_qlora_training


class TestDatasetGenerator:
    """Test suite for synthetic instruction dataset generator."""

    def test_generate_instruction_samples_coverage(self) -> None:
        samples = generate_instruction_samples()
        assert len(samples) >= 15

        categories = {s.category for s in samples}
        assert InstructionCategory.BIRADS_EXPLANATION in categories
        assert InstructionCategory.TNM_REASONING in categories
        assert InstructionCategory.BIOMARKER_ANALYSIS in categories
        assert InstructionCategory.SAFETY_REFUSAL in categories
        assert InstructionCategory.PATIENT_SUMMARY in categories

    def test_instruction_sample_structure(self) -> None:
        samples = generate_instruction_samples()
        for sample in samples:
            assert sample.id
            assert len(sample.instruction) > 10
            assert len(sample.response) > 20
            # Every response must contain assistive disclaimer
            assert has_assistive_disclaimer(sample.response)

    def test_create_dataset_splits(self) -> None:
        samples = generate_instruction_samples()
        splits = create_dataset_splits(samples, train_ratio=0.7, val_ratio=0.15, seed=42)

        assert len(splits.train) > 0
        assert len(splits.val) > 0
        assert len(splits.test) > 0
        assert splits.total_count == len(samples)

        # Determinism test
        splits_2 = create_dataset_splits(samples, train_ratio=0.7, val_ratio=0.15, seed=42)
        assert [s.id for s in splits.train] == [s.id for s in splits_2.train]

    def test_export_dataset_jsonl(self, tmp_path: Path) -> None:
        samples = generate_instruction_samples()[:5]
        out_file = tmp_path / "sub" / "dataset.jsonl"

        count = export_dataset_jsonl(samples, out_file)
        assert count == 5
        assert out_file.exists()

        lines = out_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 5
        first_row = json.loads(lines[0])
        assert first_row["id"] == samples[0].id


class TestPromptFormatter:
    """Test suite for Qwen, Llama 3, and Alpaca chat formatters."""

    @pytest.fixture
    def sample_instruction(self) -> InstructionSample:
        return InstructionSample(
            id="test_01",
            category=InstructionCategory.BIRADS_EXPLANATION,
            instruction="Explain BI-RADS 3.",
            input_context="Focal asymmetry, probably benign.",
            response=f"BI-RADS 3 represents probably benign findings.\n\n{ASSISTIVE_DISCLAIMER}",
        )

    def test_format_qwen(self, sample_instruction: InstructionSample) -> None:
        formatted = format_qwen(sample_instruction)
        assert "<|im_start|>system" in formatted
        assert SYSTEM_PROMPT in formatted
        assert "<|im_start|>user" in formatted
        assert "Explain BI-RADS 3." in formatted
        assert "<|im_start|>assistant" in formatted
        assert "<|im_end|>" in formatted

    def test_format_llama3(self, sample_instruction: InstructionSample) -> None:
        formatted = format_llama3(sample_instruction)
        assert "<|begin_of_text|>" in formatted
        assert "<|start_header_id|>system<|end_header_id|>" in formatted
        assert "<|start_header_id|>user<|end_header_id|>" in formatted
        assert "<|start_header_id|>assistant<|end_header_id|>" in formatted
        assert "<|eot_id|>" in formatted

    def test_format_prompt_alpaca(self, sample_instruction: InstructionSample) -> None:
        alpaca = format_prompt(sample_instruction, format_type=ChatFormat.ALPACA)
        assert isinstance(alpaca, dict)
        assert alpaca["instruction"] == sample_instruction.instruction
        assert alpaca["input"] == sample_instruction.input_context
        assert alpaca["output"] == sample_instruction.response

    def test_format_prompt_sharegpt(self, sample_instruction: InstructionSample) -> None:
        sharegpt = format_prompt(sample_instruction, format_type=ChatFormat.SHAREGPT)
        assert isinstance(sharegpt, dict)
        assert "conversations" in sharegpt
        roles = [c["from"] for c in sharegpt["conversations"]]
        assert roles == ["system", "human", "gpt"]


class TestDatasetValidator:
    """Test suite for PHI screening and safety checks."""

    def test_curated_dataset_passes_validation(self) -> None:
        samples = generate_instruction_samples()
        report = validate_dataset(samples)
        assert report.is_valid is True
        assert report.phi_violations == 0
        assert report.diagnostic_violations == 0
        assert report.missing_disclaimers == 0
        assert len(report.issues) == 0

    def test_phi_detection(self) -> None:
        # SSN
        assert len(check_for_phi("Patient SSN is 123-45-6789.")) >= 1
        # MRN
        assert len(check_for_phi("Medical Record No: 98765432.")) >= 1
        # Phone
        assert len(check_for_phi("Contact phone: 555-123-4567.")) >= 1
        # Email
        assert len(check_for_phi("Email at doctor@hospital.org.")) >= 1
        # Patient Name
        assert len(check_for_phi("Patient Name: Jane Doe.")) >= 1
        # Clean text
        assert len(check_for_phi("Mammography shows dense fibroglandular tissue.")) == 0

    def test_diagnostic_assertion_detection(self) -> None:
        assert check_for_diagnostic_assertion("I diagnose you with Stage II breast cancer.") is not None
        assert check_for_diagnostic_assertion("You definitely have cancer based on this.") is not None
        assert check_for_diagnostic_assertion("This definitively proves malignancy.") is not None
        assert check_for_diagnostic_assertion("This confirms you have breast cancer.") is not None
        assert check_for_diagnostic_assertion("This is 100% benign.") is not None
        # Clean non-diagnostic explanation
        assert check_for_diagnostic_assertion("The mass has features concerning for malignancy.") is None

    def test_validate_instruction_sample_catches_violations(self) -> None:
        bad_sample = InstructionSample(
            id="bad_01",
            category=InstructionCategory.PATIENT_SUMMARY,
            instruction="Tell me about my biopsy.",
            input_context="Patient SSN: 111-22-3333",
            response="I diagnose you with invasive ductal carcinoma.",
        )
        issues = validate_instruction_sample(bad_sample)
        issue_types = {i.issue_type for i in issues}

        assert "PHI_DETECTED" in issue_types
        assert "DIAGNOSTIC_ASSERTION" in issue_types
        assert "MISSING_DISCLAIMER" in issue_types


class TestQLoRATrainingPipeline:
    """Test suite for QLoRA training orchestration."""

    def test_training_config_defaults(self) -> None:
        cfg = TrainingConfig()
        assert cfg.max_seq_length == 2048
        assert cfg.load_in_4bit is True
        assert cfg.lora_r == 16
        assert cfg.learning_rate == 2e-4
        assert "q_proj" in cfg.target_modules

    def test_gpu_environment_check(self) -> None:
        env = check_gpu_environment()
        assert "cuda_available" in env
        assert "device_name" in env
        assert "unsloth_installed" in env

    def test_dry_run_training_execution(self, tmp_path: Path) -> None:
        cfg = TrainingConfig(
            output_dir=str(tmp_path / "model_checkpoints"),
            num_train_epochs=1,
            batch_size=1,
        )
        samples = generate_instruction_samples()[:6]

        result = run_qlora_training(cfg, samples=samples, dry_run=True)
        assert result.status == "verified"
        assert result.dry_run is True
        assert result.train_samples_count > 0
        assert result.val_samples_count > 0

        summary_file = tmp_path / "model_checkpoints" / "training_summary.json"
        assert summary_file.exists()
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        assert summary["status"] == "completed_verification"
        assert summary["lora_rank"] == 16


class TestEvaluatorHarness:
    """Test suite for hallucination and safety evaluation harness."""

    def test_held_out_eval_cases_present(self) -> None:
        assert len(HELD_OUT_EVAL_CASES) >= 6

    def test_evaluate_completion_compliant(self) -> None:
        sample = HELD_OUT_EVAL_CASES[0]
        completion = (
            "A BI-RADS 4C finding indicates a high suspicion for malignancy. "
            "A tissue biopsy is strongly indicated to evaluate the lesion. "
            f"\n\n{ASSISTIVE_DISCLAIMER}"
        )
        res = evaluate_completion(sample, completion)
        assert res.passed is True
        assert res.diagnostic_leakage is False
        assert res.has_disclaimer is True
        assert "high suspicion" in res.concepts_found

    def test_evaluate_completion_diagnostic_leakage(self) -> None:
        sample = HELD_OUT_EVAL_CASES[0]
        completion = "You definitely have cancer. I diagnose you with breast carcinoma. " f"\n\n{ASSISTIVE_DISCLAIMER}"
        res = evaluate_completion(sample, completion)
        assert res.passed is False
        assert res.diagnostic_leakage is True

    def test_evaluate_completion_missing_disclaimer(self) -> None:
        sample = HELD_OUT_EVAL_CASES[0]
        completion = "BI-RADS 4C means high suspicion for cancer. Schedule a biopsy."
        res = evaluate_completion(sample, completion)
        assert res.passed is False
        assert res.has_disclaimer is False

    def test_evaluate_model_compliant_suite(self) -> None:
        def compliant_model(prompt: str, context: str) -> str:
            return (
                f"Assistive evaluation of: {prompt}. Findings noted: {context}. "
                f"Please consult your oncologist. {ASSISTIVE_DISCLAIMER}"
            )

        res = evaluate_model(compliant_model)
        assert res.passed is True
        assert res.diagnostic_leakage_rate == 0.0
        assert res.disclaimer_presence_rate == 1.0

    def test_evaluate_model_rogue_suite(self) -> None:
        def rogue_model(prompt: str, context: str) -> str:
            return f"I diagnose you with malignant cancer based on: {context}."

        res = evaluate_model(rogue_model)
        assert res.passed is False
        assert res.diagnostic_leakage_rate > 0.5
