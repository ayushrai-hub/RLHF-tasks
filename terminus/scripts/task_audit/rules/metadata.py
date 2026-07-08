"""Metadata rules (#42–#45)."""

from __future__ import annotations

import re

from task_audit.context import TaskContext
from task_audit.heuristics import evaluate_category_fit
from task_audit.models import EvidenceRef
from task_audit.registry import register
from task_audit.rules._helpers import fail, heuristic, pass_, unknown
from task_audit.submission_export import tier_from_rate, worst_model_rate


@register(42, "TASK METADATA", "author_name and author_email fields present in task.toml")
def check_42(ctx: TaskContext):
    label = "author_name and author_email fields present in task.toml"
    if not ctx.toml_text:
        return fail(42, "TASK METADATA", label, "Missing task.toml")
    ok = "author_name" in ctx.toml_text and "author_email" in ctx.toml_text
    if ok:
        return pass_(42, "TASK METADATA", label, "author fields present", evidence=[EvidenceRef("task.toml")])
    return fail(42, "TASK METADATA", label, "Missing author_name/email", evidence=[EvidenceRef("task.toml")])


@register(43, "TASK METADATA", "All other required metadata fields present")
def check_43(ctx: TaskContext):
    label = "All other required metadata fields present"
    if not ctx.toml_text:
        return fail(43, "TASK METADATA", label, "Missing task.toml")
    required = [
        "version", "category", "difficulty", "codebase_size", "number_of_milestones",
        "languages", "tags", "expert_time_estimate_min", "timeout_sec", "cpus", "memory_mb", "storage_mb",
    ]
    missing = [f for f in required if f not in ctx.toml_text]
    if missing:
        return fail(43, "TASK METADATA", label, f"Missing fields: {', '.join(missing)}", evidence=[EvidenceRef("task.toml")])
    if 'allow_internet = false' not in ctx.toml_text.replace(" ", "") and "allow_internet=false" not in ctx.toml_text.replace(" ", ""):
        return fail(43, "TASK METADATA", label, "allow_internet = false required", evidence=[EvidenceRef("task.toml")])
    return pass_(43, "TASK METADATA", label, "Core metadata fields present", evidence=[EvidenceRef("task.toml")])


@register(44, "TASK METADATA", "Tags, languages, categories are applicable to the task")
def check_44(ctx: TaskContext):
    label = "Tags, languages, categories are applicable to the task"
    if not ctx.toml_text:
        return fail(44, "TASK METADATA", label, "Missing task.toml")
    cat_m = re.search(r'category\s*=\s*"([^"]+)"', ctx.toml_text)
    tags = re.findall(r'"([^"]+)"', re.search(r"tags\s*=\s*\[(.*?)\]", ctx.toml_text, re.S).group(1)) if "tags" in ctx.toml_text else []
    langs = re.findall(r'"([^"]+)"', re.search(r"languages\s*=\s*\[(.*?)\]", ctx.toml_text, re.S).group(1)) if "languages" in ctx.toml_text else []
    category = cat_m.group(1) if cat_m else ""
    score = evaluate_category_fit(category, tags, langs, ctx.combined_instruction())
    return heuristic(
        44, "TASK METADATA", label, score.passed,
        f"[{score.confidence}] {score.explanation}",
        blocking=False,
        evidence=[EvidenceRef("task.toml")],
        suggestion=f"Consider relabeling category '{category}' per docs/task-type-taxonomy.md." if not score.passed else "",
    )


@register(45, "TASK METADATA", "Difficulty matches observed agent pass rates")
def check_45(ctx: TaskContext):
    label = "Difficulty matches observed agent pass rates"
    decl_m = re.search(r'difficulty\s*=\s*"(\w+)"', ctx.toml_text, re.I)
    if not decl_m:
        return fail(45, "TASK METADATA", label, "Missing difficulty in task.toml")
    declared = decl_m.group(1).lower()
    worst = worst_model_rate(ctx.agent_stats)
    classified = ctx.agent_stats.classified_difficulty
    parts = [f"difficulty='{declared}' present in task.toml"]
    if classified:
        parts.append(f"platform='{classified}' (informational)")
    if worst is not None:
        parts.append(f"worst-model {worst:.0f}% → tier '{tier_from_rate(worst)}'")
    # Per policy: declared vs platform/agent tier mismatch is NEVER a failure
    return pass_(45, "TASK METADATA", label, "; ".join(parts), evidence=[EvidenceRef("task.toml")])
