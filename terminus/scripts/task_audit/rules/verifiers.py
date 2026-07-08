"""Verifier rules (#24–#31)."""

from __future__ import annotations

import re

from task_audit.context import TaskContext
from task_audit.heuristics import evaluate_correctness_vs_format, evaluate_spec_test_alignment
from task_audit.models import EvidenceRef
from task_audit.registry import register
from task_audit.rules._helpers import fail, heuristic, pass_, unknown

ORACLE_CONDITIONAL = re.compile(r'(\[ -d "/oracle" \]|\$EVAL_IS_ORACLE|/oracle)', re.I)
BRITTLE_EQ = re.compile(r'assert\s+\w+\s*==\s*["\'][^"\']{20,}["\']')


@register(24, "VERIFIERS", "test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path")
def check_24(ctx: TaskContext):
    label = "test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path"
    test_shs = ctx.test_sh_paths()
    if not test_shs:
        return fail(24, "VERIFIERS", label, "Missing test.sh")
    combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in test_shs)
    has_reward = "/logs/verifier/reward.txt" in combined or re.search(r"reward\.txt", combined)
    writes_both = "echo 1" in combined.replace(" ", "") or 'echo 1 >' in combined
    writes_zero = "echo 0" in combined.replace(" ", "") or 'echo 0 >' in combined
    if not has_reward:
        return fail(24, "VERIFIERS", label, "test.sh missing reward.txt write", evidence=[EvidenceRef(ctx.rel(test_shs[0]))])
    if not (writes_both or writes_zero):
        return fail(24, "VERIFIERS", label, "test.sh may not write both success/failure rewards")
    # Harbor pre-creates /logs/verifier — mkdir is recommended but not blocking
    return pass_(
        24, "VERIFIERS", label,
        "reward.txt write with failure path present (mkdir optional — Harbor provides mount)",
        evidence=[EvidenceRef(ctx.rel(test_shs[0]))],
    )


@register(25, "VERIFIERS", "Verifiers use the exact same logic for oracle and agent runs (no conditional logic)")
def check_25(ctx: TaskContext):
    label = "Verifiers use the exact same logic for oracle and agent runs (no conditional logic)"
    for ts in ctx.test_sh_paths():
        if ORACLE_CONDITIONAL.search(ts.read_text(encoding="utf-8", errors="replace")):
            return fail(25, "VERIFIERS", label, "Conditional oracle logic in test.sh", evidence=[EvidenceRef(ctx.rel(ts))])
    for tp in ctx.test_py_paths():
        if ORACLE_CONDITIONAL.search(tp.read_text(encoding="utf-8", errors="replace")):
            return fail(25, "VERIFIERS", label, f"Conditional logic in {tp.name}", evidence=[EvidenceRef(ctx.rel(tp))])
    return pass_(25, "VERIFIERS", label, "No /oracle conditional logic")


@register(26, "VERIFIERS", "Verifier applies binary rewards only (0 or 1, no partial scores)")
def check_26(ctx: TaskContext):
    label = "Verifier applies binary rewards only (0 or 1, no partial scores)"
    combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in ctx.test_sh_paths())
    if re.search(r"reward\.txt.*0\.5", combined) or re.search(r"echo\s+0\.[2-9]", combined):
        return fail(26, "VERIFIERS", label, "Non-binary reward values detected")
    return pass_(26, "VERIFIERS", label, "Binary 0/1 reward pattern")


@register(27, "VERIFIERS", "All tests are aligned with instructions (do not test unstated requirements)")
def check_27(ctx: TaskContext):
    label = "All tests are aligned with instructions (do not test unstated requirements)"
    inst = ctx.combined_instruction()
    test_src = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in ctx.test_py_paths())
    if not inst or not test_src:
        return unknown(27, "VERIFIERS", label, "Missing instruction or test files for alignment check.")
    score = evaluate_spec_test_alignment(inst, test_src)
    return heuristic(
        27, "VERIFIERS", label, score.passed, f"[{score.confidence}] {score.explanation}",
        blocking=False,
        suggestion="Document tested thresholds in instruction.md or remove phantom asserts." if not score.passed else "",
    )


@register(28, "VERIFIERS", "Tests check for correctness, not just format")
def check_28(ctx: TaskContext):
    label = "Tests check for correctness, not just format"
    test_src = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in ctx.test_py_paths())
    if not test_src:
        return fail(28, "VERIFIERS", label, "Missing test_outputs.py")
    score = evaluate_correctness_vs_format(test_src)
    return heuristic(28, "VERIFIERS", label, score.passed, f"[{score.confidence}] {score.explanation}")


@register(29, "VERIFIERS", "Tests verify behavior, not implementation (no grepping source code)")
def check_29(ctx: TaskContext):
    label = "Tests verify behavior, not implementation (no grepping source code)"
    for tp in ctx.test_py_paths():
        tpt = tp.read_text(encoding="utf-8", errors="replace")
        if re.search(r'open\s*\([^)]*main\.(py|go|rs)', tpt) or re.search(r'\.read\(\).*assert.*in', tpt):
            return fail(29, "VERIFIERS", label, "Tests may grep/read source", evidence=[EvidenceRef(ctx.rel(tp))])
    return pass_(29, "VERIFIERS", label, "No obvious implementation grep in tests")


@register(30, "VERIFIERS", "No brittle exact string matching where flexible checks would work")
def check_30(ctx: TaskContext):
    label = "No brittle exact string matching where flexible checks would work"
    brittle_files = []
    for tp in ctx.test_py_paths():
        if BRITTLE_EQ.search(tp.read_text(encoding="utf-8", errors="replace")):
            brittle_files.append(ctx.rel(tp))
    if brittle_files:
        return heuristic(
            30, "VERIFIERS", label, False,
            f"Long exact-string asserts in: {', '.join(brittle_files)}",
            suggestion="Prefer structured field checks over long literal equality.",
        )
    return heuristic(30, "VERIFIERS", label, True, "No long brittle string equality patterns detected.")


@register(31, "VERIFIERS", "Tests have informative names or docstrings")
def check_31(ctx: TaskContext):
    label = "Tests have informative names or docstrings"
    missing = ctx.test_functions_missing_docstrings()
    if missing:
        sample = ", ".join(f"{fn}@{path}" for path, fn in missing[:5])
        return fail(
            31, "VERIFIERS", label,
            f"{len(missing)} test function(s) missing docstrings: {sample}",
            evidence=[EvidenceRef(missing[0][0])],
            suggestion="Add one-line docstrings to every test_* function.",
        )
    if ctx.test_py_paths():
        return pass_(31, "VERIFIERS", label, "All test_* functions have docstrings (AST-verified)")
    return fail(31, "VERIFIERS", label, "Missing test_outputs.py")
