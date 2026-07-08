"""Oracle solution rules (#21–#23)."""

from __future__ import annotations

import re

from validate_task import RUNTIME_INSTALL_PATTERNS

from task_audit.context import TaskContext
from task_audit.models import EvidenceRef
from task_audit.registry import register
from task_audit.rules._helpers import fail, pass_, unknown

HARDCODED_ORACLE = re.compile(r'echo\s+["\'].*["\']\s*>\s*/', re.I)


@register(21, "ORACLE SOLUTION", "Oracle passes consistently (no flaky behavior)")
def check_21(ctx: TaskContext):
    label = "Oracle passes consistently (no flaky behavior)"
    if not ctx.solve_paths():
        return fail(21, "ORACLE SOLUTION", label, "Missing oracle solution")
    return unknown(
        21, "ORACLE SOLUTION", label,
        "Flake detection requires running `./scripts/terminus oracle` (not executed in read-only audit).",
        suggestion="Run oracle locally and confirm reward=1.0 across repeated trials.",
    )


@register(22, "ORACLE SOLUTION", "Oracle does not require internet or downloading packages")
def check_22(ctx: TaskContext):
    label = "Oracle does not require internet or downloading packages"
    paths = ctx.solve_paths()
    if not paths:
        return fail(22, "ORACLE SOLUTION", label, "Missing solve.sh")
    combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in paths)
    dl = [pat.pattern for pat in RUNTIME_INSTALL_PATTERNS if pat.search(combined)]
    if dl:
        return fail(22, "ORACLE SOLUTION", label, "Oracle may download/install at runtime", evidence=[EvidenceRef(ctx.rel(paths[0]))])
    return pass_(22, "ORACLE SOLUTION", label, "No network installs in solve.sh")


@register(23, "ORACLE SOLUTION", "Oracle is reflective of instruction (real implementation, not hardcoded)")
def check_23(ctx: TaskContext):
    label = "Oracle is reflective of instruction (real implementation, not hardcoded)"
    paths = ctx.solve_paths()
    if not paths:
        return fail(23, "ORACLE SOLUTION", label, "Missing solve.sh")
    combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in paths)
    if HARDCODED_ORACLE.search(combined) and "python" not in combined.lower() and "go run" not in combined.lower():
        return fail(23, "ORACLE SOLUTION", label, "Possible hardcoded echo to output path")
    derives = bool(re.search(r"(patch|python|node|go run|cargo run|npm run)", combined, re.I))
    if derives:
        return pass_(23, "ORACLE SOLUTION", label, "Oracle invokes implementation tooling (not bare echo)")
    return unknown(23, "ORACLE SOLUTION", label, "Cannot confirm oracle derives outputs — manual review needed.")
