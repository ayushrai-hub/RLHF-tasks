"""Milestone rules (#46–#49)."""

from __future__ import annotations

from validate_task import Severity

from task_audit.context import TaskContext
from task_audit.registry import register
from task_audit.rules._helpers import fail, na, pass_, unknown


@register(46, "MILESTONE TASKS", "steps/ layout present with per-milestone files (not root instruction/tests/solution)")
def check_46(ctx: TaskContext):
    label = "steps/ layout present with per-milestone files (not root instruction/tests/solution)"
    if ctx.milestone_count == 0 and not ctx.is_milestone:
        return na(46, "MILESTONE TASKS", label, "Not a milestone task (number_of_milestones = 0)")
    ms_errors = [f for f in ctx.validator_errors() if f.check == "milestone"]
    forbidden_root = []
    for name in ("instruction.md", "solution", "tests"):
        if (ctx.task_dir / name).exists():
            forbidden_root.append(name)
    if forbidden_root:
        return fail(46, "MILESTONE TASKS", label, f"Root-level forbidden: {', '.join(forbidden_root)}")
    if ms_errors:
        return fail(46, "MILESTONE TASKS", label, ms_errors[0].message)
    if ctx.is_milestone:
        return pass_(46, "MILESTONE TASKS", label, "steps/ milestone layout OK")
    return fail(46, "MILESTONE TASKS", label, "number_of_milestones>0 but no steps/ layout")


@register(47, "MILESTONE TASKS", "Each milestone has a corresponding solveN.sh file")
def check_47(ctx: TaskContext):
    label = "Each milestone has a corresponding solveN.sh file"
    if ctx.milestone_count == 0 and not ctx.is_milestone:
        return na(47, "MILESTONE TASKS", label, "Not a milestone task")
    if not ctx.is_milestone:
        return fail(47, "MILESTONE TASKS", label, "Missing steps/ layout")
    missing = []
    steps = sorted((ctx.task_dir / "steps").glob("milestone_*"))
    for i, ms in enumerate(steps, start=1):
        if not (ms / "solution" / f"solve{i}.sh").exists():
            missing.append(f"solve{i}.sh")
    if missing:
        return fail(47, "MILESTONE TASKS", label, f"Missing: {', '.join(missing)}")
    return pass_(47, "MILESTONE TASKS", label, "All solveN.sh files present")


@register(48, "MILESTONE TASKS", "Each milestone has a corresponding test_mN.py file")
def check_48(ctx: TaskContext):
    label = "Each milestone has a corresponding test_mN.py file"
    if ctx.milestone_count == 0 and not ctx.is_milestone:
        return na(48, "MILESTONE TASKS", label, "Not a milestone task")
    if not ctx.is_milestone:
        return fail(48, "MILESTONE TASKS", label, "Missing steps/ layout")
    missing = []
    steps = sorted((ctx.task_dir / "steps").glob("milestone_*"))
    for i, ms in enumerate(steps, start=1):
        if not (ms / "tests" / f"test_m{i}.py").exists():
            missing.append(f"test_m{i}.py")
    if missing:
        return fail(48, "MILESTONE TASKS", label, f"Missing: {', '.join(missing)}")
    return pass_(48, "MILESTONE TASKS", label, "All test_mN.py files present")


@register(49, "MILESTONE TASKS", "Each milestone test file is scoped only to that milestone")
def check_49(ctx: TaskContext):
    label = "Each milestone test file is scoped only to that milestone"
    if ctx.milestone_count == 0 and not ctx.is_milestone:
        return na(49, "MILESTONE TASKS", label, "Not a milestone task")
    return unknown(
        49, "MILESTONE TASKS", label,
        "Per-milestone test scope requires semantic review of test_mN.py contents.",
        suggestion="Ensure each test_mN.py only asserts outcomes for milestone N.",
    )
