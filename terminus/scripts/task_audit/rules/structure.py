"""Task structure rules (#40–#41)."""

from __future__ import annotations

from validate_task import Severity

from task_audit.context import TaskContext
from task_audit.models import EvidenceRef
from task_audit.registry import register
from task_audit.rules._helpers import fail, pass_


@register(40, "TASK STRUCTURE", "All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml)")
def check_40(ctx: TaskContext):
    label = "All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml)"
    errors = [f for f in ctx.validator_errors() if f.check == "structure"]
    if errors:
        return fail(40, "TASK STRUCTURE", label, errors[0].message, evidence=[EvidenceRef(errors[0].path or "task.toml")])
    return pass_(40, "TASK STRUCTURE", label, "Required files present")


@register(41, "TASK STRUCTURE", "No unnecessary files in parent directory (jobs/, README.md, data/, dev notes)")
def check_41(ctx: TaskContext):
    label = "No unnecessary files in parent directory (jobs/, README.md, data/, dev notes)"
    stray = []
    for name in ("jobs", "data", "dev-notes"):
        if (ctx.task_dir / name).exists():
            stray.append(name)
    if (ctx.task_dir / "README.md").exists():
        stray.append("README.md")
    if stray:
        return fail(41, "TASK STRUCTURE", label, f"Stray files: {', '.join(stray)}", blocking=False)
    return pass_(41, "TASK STRUCTURE", label, "No obvious stray parent files")
