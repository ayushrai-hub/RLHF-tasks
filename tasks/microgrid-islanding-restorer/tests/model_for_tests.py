import sys

sys.path.insert(0, "/app/task_file/scripts")

from model import evaluate as _base_evaluate  # noqa: E402


def evaluate(input_dir, output_dir):
    result = _base_evaluate(input_dir, output_dir)
    score = result.get("total_score", 0.0)
    if result.get("critical_spread_score", 0.0) < 1.0:
        score *= 0.55
    if result.get("load_balance_score", 0.0) < 0.32:
        score *= 0.7
    result["total_score_strict"] = round(max(0.0, min(1.0, score)), 4)
    return result
