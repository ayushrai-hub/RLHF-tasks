"""Difficulty rules (#54–#55)."""

from __future__ import annotations

from task_audit.context import TaskContext
from task_audit.registry import register
from task_audit.rules._helpers import fail, pass_, unknown
from task_audit.submission_export import tier_from_rate, worst_model_rate


@register(54, "TASK DIFFICULTY", "Task is not too easy (not >80% combined pass rate consistently)")
def check_54(ctx: TaskContext):
    label = "Task is not too easy (not >80% combined pass rate consistently)"
    worst = worst_model_rate(ctx.agent_stats)
    if worst is None:
        return unknown(
            54, "TASK DIFFICULTY", label,
            "Agent pass rates require --report submission export.",
            suggestion="Run agent tests and attach entire-report.txt for #54 evaluation.",
        )
    if worst > 80:
        return fail(54, "TASK DIFFICULTY", label, f"Worst-model pass rate {worst:.0f}% > 80% (too easy)", blocking=True)
    return pass_(54, "TASK DIFFICULTY", label, f"Worst-model {worst:.0f}% ≤ 80%")


@register(55, "TASK DIFFICULTY", "Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck)")
def check_55(ctx: TaskContext):
    label = "Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck)"
    worst = worst_model_rate(ctx.agent_stats)
    if worst is not None and worst == 0 and ctx.agent_stats.solvable:
        return unknown(
            55, "TASK DIFFICULTY", label,
            "0% pass rate but marked solvable — may indicate hardness or spec gaps; human fairness review required.",
            suggestion="Review instruction sufficiency analysis in submission export.",
        )
    return unknown(
        55, "TASK DIFFICULTY", label,
        "Fairness assessment requires human judgment of instructions, environment, and agent trajectories.",
    )
