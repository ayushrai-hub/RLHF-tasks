import sys

sys.path.insert(0, "/tests")
from model import evaluate  # noqa: E402


def strict_evaluate(input_dir, output_dir):
    """Apply strict assignment-quality gates on top of the base score."""
    base = evaluate(input_dir, output_dir)
    if "error" in base or "penalty" in base:
        return {**base, "total_score_strict": 0.0}
    score = base["total_score"]
    if base.get("affinity_score", 0.0) < 0.75:
        score *= 0.55
    if base.get("cpu_balance_score", 0.0) < 0.70:
        score *= 0.65
    return {**base, "total_score_strict": round(max(0.0, min(1.0, score)), 4)}
