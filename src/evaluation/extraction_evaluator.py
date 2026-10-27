"""Extraction benchmark evaluator measuring precision, recall, and F1 across clinical entity categories.

Validates against PRD §6 target: Entity extraction precision/recall >= 0.85 on held-out annotated set.
"""

from __future__ import annotations

from src.core.logging import get_logger
from src.evaluation.gold_dataset import GOLD_BENCHMARK_CASES, GoldBenchmarkCase
from src.evaluation.schemas import EntityMetric, ExtractionEvaluationResult
from src.extraction.engine import extract_entities

logger = get_logger(__name__)


class ExtractionEvaluator:
    """Evaluates extraction precision, recall, and F1 score against gold-standard annotations."""

    def evaluate(self, cases: list[GoldBenchmarkCase] | None = None) -> ExtractionEvaluationResult:
        """Run extraction across gold benchmark cases and calculate precision/recall metrics.

        Args:
            cases: Optional custom benchmark cases (defaults to GOLD_BENCHMARK_CASES).

        Returns:
            ExtractionEvaluationResult with per-category and macro-averaged metrics.
        """
        eval_cases = cases or GOLD_BENCHMARK_CASES
        categories = ["birads", "tnm_staging", "biomarkers", "tumor_dimensions", "lymph_nodes"]
        stats = {c: {"tp": 0, "fp": 0, "fn": 0} for c in categories}
        total_gold = 0
        total_extracted = 0

        for case in eval_cases:
            extracted = extract_entities(case.text)

            # Map extracted items by category
            extracted_map: dict[str, list[str]] = {
                "birads": [b.category for b in extracted.birads],
                "tnm_staging": [t.raw_stage for t in extracted.tnm_staging],
                "biomarkers": [b.name for b in extracted.biomarkers],
                "tumor_dimensions": [
                    str(t.primary_size_mm) for t in extracted.tumor_dimensions if t.primary_size_mm is not None
                ],
                "lymph_nodes": [
                    f"{ln.nodes_positive}/{ln.nodes_examined}"
                    for ln in extracted.lymph_nodes
                    if ln.nodes_positive is not None and ln.nodes_examined is not None
                ],
            }

            for cat in categories:
                total_extracted += len(extracted_map[cat])

            # Evaluate each gold annotation
            for gold in case.expected_entities:
                total_gold += 1
                cat = gold.category
                exp_val = gold.expected_value
                found_match = False

                if cat == "birads":
                    found_match = exp_val in extracted_map[cat]
                elif cat == "tnm_staging":
                    found_match = any(exp_val in act for act in extracted_map[cat])
                elif cat == "biomarkers":
                    found_match = exp_val in extracted_map[cat]
                elif cat == "tumor_dimensions":
                    try:
                        exp_float = float(exp_val)
                        found_match = any(abs(float(act) - exp_float) < 1.0 for act in extracted_map[cat])
                    except ValueError:
                        found_match = exp_val in extracted_map[cat]
                elif cat == "lymph_nodes":
                    found_match = exp_val in extracted_map[cat]

                if found_match:
                    stats[cat]["tp"] += 1
                else:
                    stats[cat]["fn"] += 1

            # Check false positives
            for cat in categories:
                gold_vals = [g.expected_value for g in case.expected_entities if g.category == cat]
                for act_val in extracted_map[cat]:
                    # Match logic for FP check
                    if cat == "tnm_staging":
                        is_valid = any(g in act_val for g in gold_vals)
                    elif cat == "tumor_dimensions":
                        try:
                            act_float = float(act_val)
                            is_valid = any(abs(float(g) - act_float) < 1.0 for g in gold_vals)
                        except ValueError:
                            is_valid = act_val in gold_vals
                    else:
                        is_valid = act_val in gold_vals

                    if not is_valid:
                        stats[cat]["fp"] += 1

        # Calculate per-category metrics
        entity_metrics: dict[str, EntityMetric] = {}
        for cat in categories:
            tp = stats[cat]["tp"]
            fp = stats[cat]["fp"]
            fn = stats[cat]["fn"]

            prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
            rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
            f1 = round((2 * prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0

            entity_metrics[cat] = EntityMetric(
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision=prec,
                recall=rec,
                f1_score=f1,
            )

        # Macro averages
        macro_prec = round(sum(m.precision for m in entity_metrics.values()) / len(categories), 4)
        macro_rec = round(sum(m.recall for m in entity_metrics.values()) / len(categories), 4)
        macro_denom = macro_prec + macro_rec
        macro_f1 = round((2 * macro_prec * macro_rec) / macro_denom, 4) if macro_denom > 0 else 0.0

        # PRD §6 targets precision/recall >= 0.85
        passed = macro_prec >= 0.85 and macro_rec >= 0.85

        logger.info(
            "Extraction evaluation complete",
            macro_precision=macro_prec,
            macro_recall=macro_rec,
            macro_f1=macro_f1,
            passed=passed,
        )

        return ExtractionEvaluationResult(
            entity_metrics=entity_metrics,
            macro_precision=macro_prec,
            macro_recall=macro_rec,
            macro_f1=macro_f1,
            total_gold_entities=total_gold,
            total_extracted_entities=total_extracted,
            passed_target=passed,
        )
