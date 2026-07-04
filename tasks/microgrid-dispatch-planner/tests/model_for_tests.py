"""Strict scoring wrapper matching dispatcher/docs/scoring.md."""

import sys

sys.path.insert(0, "/app/task_file/scripts")
from model import evaluate


def strict_evaluate(input_dir, output_dir):
    base = evaluate(input_dir, output_dir)
    if "error" in base:
        return {**base, "total_score_strict": 0.0}

    score = base["total_score"] * 0.94

    # The frequency setpoint must match the settled grid frequency precisely.
    if base.get("freq_gap", 1.0) > 0.04:
        score *= 0.50

    # The plan must run cleanly, not merely meet the emission budget.
    if base.get("efficiency_score", 0.0) < 0.82:
        score *= 0.55
    # Supply must be balanced tightly to demand.
    if base.get("service_score", 0.0) < 0.92:
        score *= 0.85
    # Renewables must carry the bulk of the load.
    if base.get("renewable_fraction", 0.0) < 0.55:
        score *= 0.90
    # Leaning on the degraded units is penalised further.
    if base.get("degraded_output", 0.0) > 800.0:
        score *= 0.85

    strict = round(max(0.0, min(1.0, score)), 4)
    return {**base, "total_score_strict": strict}
