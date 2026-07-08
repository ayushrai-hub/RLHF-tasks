"""Rubric rules (#32–#39) — require platform rubric via --report or --rubric."""

from __future__ import annotations

import re

from rubric_points import RUBRIC_POSITIVE_CAP
from task_audit.models import EvidenceRef
from task_audit.registry import register
from task_audit.rules._helpers import fail, heuristic, na, pass_, unknown

RUBRIC_META_PATTERNS = [
    re.compile(r"task\.toml", re.I),
    re.compile(r"instruction\.md", re.I),
    re.compile(r"\bthe task instructions\b", re.I),
    re.compile(r"\bconstraint from instructions\b", re.I),
    re.compile(r"\btask constraint\b", re.I),
]


@register(32, "RUBRICS", "Rubrics contain at least 3 negative penalty criteria")
def check_32(ctx: TaskContext):
    label = "Rubrics contain at least 3 negative penalty criteria"
    text = ctx.rubric_text()
    if not text:
        return unknown(32, "RUBRICS", label, "No rubric in task folder or --report export.", suggestion="Provide --report or --rubric for rubric checks.")
    negatives = re.findall(r",\s*-\d", text)
    if len(negatives) >= 3:
        return pass_(32, "RUBRICS", label, f"{len(negatives)} negative criteria")
    return fail(32, "RUBRICS", label, f"Only {len(negatives)} negative criteria (need ≥3)", blocking=True)


@register(33, "RUBRICS", "Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5}")
def check_33(ctx: TaskContext):
    label = "Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5}"
    text = ctx.rubric_text()
    if not text:
        return unknown(33, "RUBRICS", label, "No rubric available.")
    scores = re.findall(r",\s*([+-]?\d+)\s*$", text, re.M)
    invalid = [s for s in scores if abs(int(s)) not in (1, 2, 3, 5)]
    if invalid:
        return fail(33, "RUBRICS", label, f"Invalid scores: {invalid[:5]}")
    return pass_(33, "RUBRICS", label, "All scores in ±1,2,3,5")


@register(34, "RUBRICS", "Each rubric criterion is one line starting with Agent, comma, then score")
def check_34(ctx: TaskContext):
    label = "Each rubric criterion is one line starting with Agent, comma, then score"
    text = ctx.rubric_text()
    if not text:
        return unknown(34, "RUBRICS", label, "No rubric available.")
    agent_lines = [ln for ln in text.splitlines() if ln.strip().lower().startswith("agent")]
    bad = [ln for ln in agent_lines if not re.match(r"^Agent .+,\s*[+-]\d+\s*$", ln.strip())]
    if len(agent_lines) < 3:
        return fail(34, "RUBRICS", label, f"Only {len(agent_lines)} Agent lines")
    if bad:
        return fail(34, "RUBRICS", label, f"Malformed lines: {bad[0][:60]}...")
    return pass_(34, "RUBRICS", label, f"{len(agent_lines)} properly formatted Agent lines")


@register(35, "RUBRICS", "Rubric criteria are detailed and precise")
def check_35(ctx: TaskContext):
    label = "Rubric criteria are detailed and precise"
    text = ctx.rubric_text()
    if not text:
        return unknown(35, "RUBRICS", label, "No rubric available.")
    rp = ctx.rubric_positive
    if rp.found and rp.over_cap:
        return fail(
            35, "RUBRICS", label,
            f"Positive total {rp.total_positive_pts} exceeds cap {rp.cap_detail}",
            blocking=True,
            suggestion=f"Trim positive criteria to ≤{RUBRIC_POSITIVE_CAP} total (currently {rp.total_positive_pts}).",
        )
    if rp.found:
        return pass_(35, "RUBRICS", label, f"Positive points {rp.total_positive_pts} within cap")
    return heuristic(35, "RUBRICS", label, True, "Rubric present; positive cap not computed")


@register(36, "RUBRICS", "Rubric criteria use positive language (not Agent does not do X, +1)")
def check_36(ctx: TaskContext):
    label = "Rubric criteria use positive language (not Agent does not do X, +1)"
    text = ctx.rubric_text()
    if not text:
        return unknown(36, "RUBRICS", label, "No rubric available.")
    bad_pos = re.findall(r"^Agent (?:does not|doesn't|fails to).+,\s*\+", text, re.M | re.I)
    if bad_pos:
        return fail(36, "RUBRICS", label, "Positive score paired with negative phrasing")
    return pass_(36, "RUBRICS", label, "No positive-score negative phrasing detected")


@register(37, "RUBRICS", "Rubric does not reference testing logic or /tests/ directory")
def check_37(ctx: TaskContext):
    label = "Rubric does not reference testing logic or /tests/ directory"
    text = ctx.rubric_text()
    if not text:
        return unknown(37, "RUBRICS", label, "No rubric available.")
    if re.search(r"/tests/|pytest", text, re.I):
        return fail(37, "RUBRICS", label, "References /tests/ or pytest")
    return pass_(37, "RUBRICS", label, "No /tests/ references")


@register(38, "RUBRICS", "Rubric does not reference metadata (task.toml) or instruction.md")
def check_38(ctx: TaskContext):
    label = "Rubric does not reference metadata (task.toml) or instruction.md"
    text = ctx.rubric_text()
    if not text:
        return unknown(38, "RUBRICS", label, "No rubric available.")
    for pat in RUBRIC_META_PATTERNS:
        m = pat.search(text)
        if m:
            return fail(
                38, "RUBRICS", label,
                f"References task metadata/instructions: '{m.group(0)}'",
                suggestion="Describe agent behavior directly without citing instruction.md or task.toml.",
            )
    return pass_(38, "RUBRICS", label, "No metadata/instruction references")


@register(39, "RUBRICS", "Rubric does not mention oracle or NOP runs")
def check_39(ctx: TaskContext):
    label = "Rubric does not mention oracle or NOP runs"
    text = ctx.rubric_text()
    if not text:
        return unknown(39, "RUBRICS", label, "No rubric available.")
    if re.search(r"\boracle\b|\bNOP\b", text, re.I):
        return fail(39, "RUBRICS", label, "Mentions oracle/NOP")
    return pass_(39, "RUBRICS", label, "No oracle/NOP mentions")
