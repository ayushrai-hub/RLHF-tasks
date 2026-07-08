"""Instruction prompt rules (#1–#12)."""

from __future__ import annotations

import re

from validate_task import HINT_PATTERNS

from task_audit.context import TaskContext
from task_audit.heuristics import (
    CANARY_PATTERNS,
    RELATIVE_PATH,
    evaluate_concise,
    evaluate_natural_tone,
    evaluate_well_specified,
)
from task_audit.models import EvidenceRef
from task_audit.registry import register
from task_audit.rules._helpers import fail, heuristic, pass_, unknown


def _ev(ctx: TaskContext) -> list[EvidenceRef]:
    return [EvidenceRef(ctx.rel(p)) for p in ctx.instruction_paths()]


@register(1, "INSTRUCTION PROMPT", "Instruction is concise (1 sentence to 3 paragraphs max)")
def check_01(ctx: TaskContext):
    label = "Instruction is concise (1 sentence to 3 paragraphs max)"
    if not ctx.instruction_paths():
        return fail(1, "INSTRUCTION PROMPT", label, "Missing instruction.md", evidence=[EvidenceRef("instruction.md")])
    score = evaluate_concise(ctx.combined_instruction())
    return heuristic(
        1, "INSTRUCTION PROMPT", label, score.passed,
        f"[{score.confidence}] {score.explanation}",
        blocking=not score.passed and score.confidence == "high",
        evidence=_ev(ctx),
        suggestion="Trim to ≤3 problem paragraphs; keep requirement bullets concise." if not score.passed else "",
    )


@register(2, "INSTRUCTION PROMPT", "Instruction reads like a natural prompt, not a spec document")
def check_02(ctx: TaskContext):
    label = "Instruction reads like a natural prompt, not a spec document"
    if not ctx.instruction_paths():
        return fail(2, "INSTRUCTION PROMPT", label, "Missing instruction.md")
    score = evaluate_natural_tone(ctx.combined_instruction())
    if score.passed:
        return heuristic(2, "INSTRUCTION PROMPT", label, True, f"[{score.confidence}] {score.explanation}", evidence=_ev(ctx))
    return heuristic(
        2, "INSTRUCTION PROMPT", label, False,
        f"[{score.confidence}] {score.explanation}",
        blocking=score.confidence == "high",
        evidence=_ev(ctx),
        suggestion="Rewrite as an on-call/incident brief; remove spec-style section headers.",
    )


@register(3, "INSTRUCTION PROMPT", "No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks)")
def check_03(ctx: TaskContext):
    label = "No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks)"
    combined = ctx.combined_instruction()
    if not combined:
        return fail(3, "INSTRUCTION PROMPT", label, "Missing instruction")
    h2 = len(re.findall(r"^##\s", combined, re.M))
    h3 = len(re.findall(r"^###\s", combined, re.M))
    tables = combined.count("|---")
    code_fences = combined.count("```")
    if h2 > 2 or h3 > 3 or tables > 0 or code_fences > 4:
        return fail(
            3, "INSTRUCTION PROMPT", label,
            f"Heavy markdown: ##={h2}, ###={h3}, tables={tables}, code_blocks={code_fences // 2}",
            evidence=_ev(ctx),
            suggestion="Use plain prose and bullet lists; move schemas to environment docs.",
        )
    return pass_(3, "INSTRUCTION PROMPT", label, "No excessive markdown detected", evidence=_ev(ctx))


@register(4, "INSTRUCTION PROMPT", "No step by step instructions telling the agent what developer steps to take")
def check_04(ctx: TaskContext):
    label = "No step by step instructions telling the agent what developer steps to take"
    combined = ctx.combined_instruction()
    step_hits = [pat.pattern for pat in HINT_PATTERNS if pat.search(combined)]
    if step_hits:
        return fail(4, "INSTRUCTION PROMPT", label, f"Step/hint patterns: {step_hits[:3]}", evidence=_ev(ctx))
    return pass_(4, "INSTRUCTION PROMPT", label, "No step-by-step walkthrough patterns", evidence=_ev(ctx))


@register(5, "INSTRUCTION PROMPT", "No hints or solving strategies (describes WHAT to build, not HOW)")
def check_05(ctx: TaskContext):
    label = "No hints or solving strategies (describes WHAT to build, not HOW)"
    combined = ctx.combined_instruction()
    if re.search(r"hint:|look for:|you should (run|edit)", combined, re.I):
        return fail(5, "INSTRUCTION PROMPT", label, "Explicit hint language found", evidence=_ev(ctx))
    how_count = len(re.findall(r"\b(edit|modify|open|change)\s+[\w/]+\.(py|js|go|rs|java)\b", combined, re.I))
    if how_count >= 4:
        return heuristic(
            5, "INSTRUCTION PROMPT", label, False,
            f"Multiple file-edit directives ({how_count}) — may over-specify HOW.",
            evidence=_ev(ctx),
            suggestion="State outcomes and artifact paths; let agent discover modules.",
        )
    return heuristic(5, "INSTRUCTION PROMPT", label, True, "No explicit hint language; limited HOW directives.", evidence=_ev(ctx))


@register(6, "INSTRUCTION PROMPT", "No design doc style tables mapping inputs to outputs")
def check_06(ctx: TaskContext):
    label = "No design doc style tables mapping inputs to outputs"
    combined = ctx.combined_instruction()
    if combined.count("|---") > 0 or re.search(r"\|\s*\w+\s*\|\s*\w+\s*\|", combined):
        return fail(6, "INSTRUCTION PROMPT", label, "Input/output mapping tables present", evidence=_ev(ctx))
    return pass_(6, "INSTRUCTION PROMPT", label, "No design-doc tables", evidence=_ev(ctx))


@register(7, "INSTRUCTION PROMPT", "Instruction is well specified (goal is clear and obvious)")
def check_07(ctx: TaskContext):
    label = "Instruction is well specified (goal is clear and obvious)"
    if not ctx.instruction_paths():
        return fail(7, "INSTRUCTION PROMPT", label, "Missing instruction")
    score = evaluate_well_specified(ctx.combined_instruction())
    return heuristic(
        7, "INSTRUCTION PROMPT", label, score.passed,
        f"[{score.confidence}] {score.explanation}",
        blocking=not score.passed and score.confidence == "high",
        evidence=_ev(ctx),
    )


@register(8, "INSTRUCTION PROMPT", "Instruction is interesting (useful to some group of developers)")
def check_08(ctx: TaskContext):
    label = "Instruction is interesting (useful to some group of developers)"
    return unknown(
        8, "INSTRUCTION PROMPT", label,
        "Subjective quality — requires human reviewer judgment.",
        suggestion="Confirm the scenario is realistic and useful to a developer audience.",
    )


@register(9, "INSTRUCTION PROMPT", "Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task)")
def check_09(ctx: TaskContext):
    label = "Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task)"
    return unknown(
        9, "INSTRUCTION PROMPT", label,
        "Corpus uniqueness cannot be verified from task artifacts alone.",
        suggestion="Compare against TB2/TB3/Edition 1 task index before submission.",
    )


@register(10, "INSTRUCTION PROMPT", "All paths in instruction are absolute (not relative)")
def check_10(ctx: TaskContext):
    label = "All paths in instruction are absolute (not relative)"
    combined = ctx.combined_instruction()
    if RELATIVE_PATH.search(combined):
        return fail(10, "INSTRUCTION PROMPT", label, "Relative paths found (./ ../ ~/)", evidence=_ev(ctx))
    if re.search(r"/[\w.-]+", combined):
        return pass_(10, "INSTRUCTION PROMPT", label, "Absolute paths present; no relative paths", evidence=_ev(ctx))
    return fail(10, "INSTRUCTION PROMPT", label, "No absolute paths detected", evidence=_ev(ctx))


@register(11, "INSTRUCTION PROMPT", "Task name does not appear in instruction.md")
def check_11(ctx: TaskContext):
    label = "Task name does not appear in instruction.md"
    name = ctx.task_dir.name.lower()
    toml_name = ""
    m = re.search(r'name\s*=\s*"([^"]+)"', ctx.toml_text)
    if m:
        toml_name = m.group(1).lower()
    combined = ctx.combined_instruction().lower()
    if name in combined or (toml_name and toml_name in combined):
        return fail(11, "INSTRUCTION PROMPT", label, f"Task name appears in instruction", evidence=_ev(ctx))
    return pass_(11, "INSTRUCTION PROMPT", label, "Task name not in instruction", evidence=_ev(ctx))


@register(12, "INSTRUCTION PROMPT", "No canary string in instruction.md")
def check_12(ctx: TaskContext):
    label = "No canary string in instruction.md"
    combined = ctx.combined_instruction()
    if any(p.search(combined) for p in CANARY_PATTERNS):
        return fail(12, "INSTRUCTION PROMPT", label, "Canary string pattern detected", evidence=_ev(ctx))
    return pass_(12, "INSTRUCTION PROMPT", label, "No canary patterns", evidence=_ev(ctx))
