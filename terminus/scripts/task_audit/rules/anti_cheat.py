"""Anti-cheating rules (#50–#53)."""

from __future__ import annotations

import re

from task_audit.context import TaskContext
from task_audit.models import EvidenceRef
from task_audit.registry import register
from task_audit.rules._helpers import fail, pass_, unknown

GIT_CLONE_UNPINNED = re.compile(r"git\s+clone[^;|&]*$", re.M)


@register(50, "ANTI CHEATING", "Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile)")
def check_50(ctx: TaskContext):
    label = "Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile)"
    text = ctx.dockerfile_text()
    copy_tests = any(
        re.match(r"^\s*COPY\s+.*\btests\b", ln, re.I)
        for ln in text.splitlines()
        if not ln.strip().startswith("#")
    )
    if copy_tests:
        return fail(50, "ANTI CHEATING", label, "COPY tests/ in Dockerfile", evidence=[EvidenceRef("environment/Dockerfile")])
    dockerignore = ctx.task_dir / "environment" / ".dockerignore"
    if dockerignore.exists() and "tests" in dockerignore.read_text(encoding="utf-8"):
        return pass_(50, "ANTI CHEATING", label, "No tests COPY; .dockerignore excludes tests")
    return pass_(50, "ANTI CHEATING", label, "No tests COPY in image")


@register(51, "ANTI CHEATING", "Solution or ground truth answers are not accessible in the environment")
def check_51(ctx: TaskContext):
    label = "Solution or ground truth answers are not accessible in the environment"
    dockerignore = ctx.task_dir / "environment" / ".dockerignore"
    if dockerignore.exists():
        di = dockerignore.read_text(encoding="utf-8", errors="replace")
        if "solution" in di and "tests" in di:
            return pass_(51, "ANTI CHEATING", label, ".dockerignore excludes solution/ and tests/")
    return unknown(51, "ANTI CHEATING", label, "Manual review needed for ground-truth leakage in env docs/comments.")


@register(52, "ANTI CHEATING", "Agent cannot modify input data to trivially pass tests")
def check_52(ctx: TaskContext):
    label = "Agent cannot modify input data to trivially pass tests"
    return unknown(
        52, "ANTI CHEATING", label,
        "Requires reviewing whether test inputs are writable/immutable in the container.",
        suggestion="Confirm golden inputs are read-only or tests use ephemeral fixtures.",
    )


@register(53, "ANTI CHEATING", "Git repos pinned to specific commit (no unpinned git clone)")
def check_53(ctx: TaskContext):
    label = "Git repos pinned to specific commit (no unpinned git clone)"
    text = ctx.dockerfile_text()
    if GIT_CLONE_UNPINNED.search(text) and "git checkout" not in text.lower():
        return fail(53, "ANTI CHEATING", label, "Unpinned git clone in Dockerfile")
    if "git clone" in text.lower():
        return pass_(53, "ANTI CHEATING", label, "git clone with checkout pin") if "git checkout" in text.lower() else unknown(53, "ANTI CHEATING", label, "Verify git pin manually")
    return pass_(53, "ANTI CHEATING", label, "No git clone in Dockerfile")
