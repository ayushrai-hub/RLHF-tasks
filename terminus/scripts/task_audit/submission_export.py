"""Submission export parsing — extracted from review_checklist for reuse."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class AgentStats:
    models: dict[str, float] = field(default_factory=dict)
    oracle_rate: float | None = None
    nop_rate: float | None = None
    classified_difficulty: str | None = None
    solvable: bool | None = None


@dataclass
class SubmissionExport:
    difficulty_explanation: str = ""
    solution_explanation: str = ""
    verification_explanation: str = ""
    difficulty_check: str = ""
    instruction_sufficiency: str = ""
    quality_check: str = ""
    review_report: str = ""
    test_quality: str = ""
    platform_rubric: str = ""
    agent_review: str = ""
    comments_for_reviewer: str = ""
    reviewer_feedback: str = ""
    raw: str = ""


_EXPORT_MARKERS: list[tuple[str, re.Pattern[str]]] = [
    ("difficulty_explanation", re.compile(r"^Difficulty Explanation \(optional\)")),
    ("solution_explanation", re.compile(r"^Solution Explanation \(optional\)")),
    ("verification_explanation", re.compile(r"^Verification Explanation \(optional\)")),
    ("comments_for_reviewer", re.compile(r"^Comments for Reviewer(\s*\(optional\))?\s*$", re.I)),
    ("reviewer_feedback", re.compile(r"^Reviewer Feedback(\s*\(optional\))?\s*$", re.I)),
    ("difficulty_check", re.compile(r"^Difficulty:\s*[✅❌]")),
    ("quality_check", re.compile(r"^##?\s*Quality Check Results")),
    ("review_report", re.compile(r"REVIEW REPORT:\s*\S")),
    ("test_quality", re.compile(r"TEST QUALITY REVIEW:")),
    ("agent_review", re.compile(r"^Agent review\s*$", re.I)),
    ("platform_rubric", re.compile(r"^Agent-generated rubric", re.I)),
]

RUBRIC_HEADER_RE = re.compile(r"^# Rubric \d+\s*$")
AGENT_LINE_RE = re.compile(r"^Agent .+,\s*[+-]\d+\s*$")


def _extract_trailing_agent_rubric(text: str) -> str:
    lines = text.splitlines()
    collected: list[str] = []
    for line in reversed(lines):
        stripped = line.strip()
        if AGENT_LINE_RE.match(stripped):
            collected.insert(0, stripped)
        elif collected:
            break
    return "\n".join(collected) if len(collected) >= 3 else ""


def parse_submission_export(text: str) -> SubmissionExport:
    export = SubmissionExport(raw=text)
    if not text.strip():
        return export

    lines = text.splitlines()
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        for key, pat in _EXPORT_MARKERS:
            if pat.search(stripped) or pat.match(stripped):
                hits.append((i, key))
                break
        if RUBRIC_HEADER_RE.match(stripped):
            hits.append((i, "platform_rubric"))

    if not hits:
        export.platform_rubric = _extract_trailing_agent_rubric(text)
        export.difficulty_check = text
        return export

    hits.sort(key=lambda x: x[0])
    seen: set[str] = set()
    ordered: list[tuple[int, str]] = []
    for pos, key in hits:
        if key not in seen:
            seen.add(key)
            ordered.append((pos, key))

    for idx, (start, key) in enumerate(ordered):
        end = ordered[idx + 1][0] if idx + 1 < len(ordered) else len(lines)
        chunk = "\n".join(lines[start:end]).strip()
        setattr(export, key, chunk)

    if not export.instruction_sufficiency and export.difficulty_check:
        m = re.search(
            r"(Analysis on Agent Failures:.*|Task Instruction Sufficiency:.*)",
            export.difficulty_check,
            re.S,
        )
        if m:
            export.instruction_sufficiency = m.group(1).strip()

    if not export.platform_rubric.strip():
        export.platform_rubric = _extract_trailing_agent_rubric(text)

    return export


def parse_report(text: str, export: SubmissionExport | None = None) -> AgentStats:
    scope = export.difficulty_check if export and export.difficulty_check.strip() else text
    stats = AgentStats()
    for m in re.finditer(r"(terminus-[\w.-]+|terminus-gpt5-5):\s*([\d.]+)%", scope, re.I):
        stats.models[m.group(1)] = float(m.group(2))
    for m in re.finditer(r"•\s*(terminus-[\w.-]+|terminus-gpt5-5):\s*([\d.]+)%", scope, re.I):
        stats.models[m.group(1)] = float(m.group(2))

    om = re.search(r"oracle:\s*([\d.]+)%", scope, re.I)
    if om:
        stats.oracle_rate = float(om.group(1))
    nm = re.search(r"nop:\s*([\d.]+)%", scope, re.I)
    if nm:
        stats.nop_rate = float(nm.group(1))

    dm = re.search(r"Difficulty:\s*[✅❌]?\s*(EASY|MEDIUM|HARD|TRIVIAL)", scope, re.I)
    if dm:
        stats.classified_difficulty = dm.group(1).lower()

    if re.search(r"Solvable.*✅|solvable.*yes", scope, re.I):
        stats.solvable = True
    elif re.search(r"Unsolvable|not solvable", scope, re.I):
        stats.solvable = False

    return stats


def worst_model_rate(stats: AgentStats) -> float | None:
    agent_rates = [
        v for k, v in stats.models.items()
        if "oracle" not in k.lower() and "nop" not in k.lower()
    ]
    return min(agent_rates) if agent_rates else None


def tier_from_rate(rate: float) -> str:
    if rate <= 20:
        return "hard"
    if rate <= 60:
        return "medium"
    if rate <= 80:
        return "easy"
    return "trivial"
