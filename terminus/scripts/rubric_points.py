#!/usr/bin/env python3
"""Sum positive rubric points from platform rubrics (e.g. entire-report.txt).

Only ``Agent …, +N`` lines count toward the 10–40 positive band.
Negative criteria are tracked separately (≥3 required) and are NOT
subtracted from the positive total.

Main blocker rule: **>40** positive points (40 exactly passes).
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

RUBRIC_POSITIVE_FLOOR = 10
RUBRIC_POSITIVE_CAP = 40

RUBRIC_HEADER_RE = re.compile(r"^# Rubric \d+\s*$")
RUBRIC_BLOCK_HEADER_RE = re.compile(r"^# Rubric (\d+)\s*$")
RUBRIC_POSITIVE_LINE_RE = re.compile(r"^Agent .+, \+(\d+)\s*$")
AGENT_LINE_RE = re.compile(r"^Agent .+,\s*[+-]\d+\s*$")

_EXPORT_RUBRIC_MARKER = re.compile(r"^Agent-generated rubric", re.I)


@dataclass
class RubricPositiveAnalysis:
    """Positive-point summary for a platform rubric."""

    total_positive_pts: int = 0
    positive_line_count: int = 0
    per_block_positive_pts: dict[int, int] = field(default_factory=dict)
    rubric_text: str = ""
    rubric_source: str = ""
    num_milestones: int = 0
    over_cap: bool = False
    cap_detail: str = ""
    found: bool = False

    @property
    def cap_status(self) -> str:
        if not self.found:
            return "no rubric"
        if self.over_cap:
            return "FAIL (>40)"
        if self.total_positive_pts < RUBRIC_POSITIVE_FLOOR:
            return f"LOW (<{RUBRIC_POSITIVE_FLOOR})"
        return f"PASS ({self.total_positive_pts}/{RUBRIC_POSITIVE_CAP})"


def sum_positive_rubric_points(rubric_text: str) -> tuple[int, int, dict[int, int]]:
    """Sum only ``Agent …, +N`` lines.

    Returns ``(total_pts, line_count, per_block_pts)``.
    Block keys come from ``# Rubric N`` headers; lines before any header use block 0.
    """
    total = 0
    line_count = 0
    blocks: dict[int, int] = {}
    current_block = 0

    for raw in rubric_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        hm = RUBRIC_BLOCK_HEADER_RE.match(line)
        if hm:
            current_block = int(hm.group(1))
            blocks.setdefault(current_block, 0)
            continue
        if not line.startswith("Agent"):
            continue
        m = RUBRIC_POSITIVE_LINE_RE.match(line)
        if not m:
            continue
        score = int(m.group(1))
        total += score
        line_count += 1
        blocks[current_block] = blocks.get(current_block, 0) + score

    return total, line_count, blocks


def analyze_rubric_positives(
    rubric_text: str,
    *,
    num_milestones: int = 0,
    rubric_source: str = "",
) -> RubricPositiveAnalysis:
    """Analyze positive points; set ``over_cap`` only when strictly >40."""
    text = rubric_text.strip()
    if not text:
        return RubricPositiveAnalysis(rubric_source=rubric_source)

    total, line_count, blocks = sum_positive_rubric_points(text)
    # Drop block 0 unless it has points (lines before first # Rubric header)
    per_block = {k: v for k, v in blocks.items() if k > 0 or (k == 0 and v > 0)}

    over_cap = False
    cap_detail = ""

    if num_milestones > 0:
        named_blocks = {k: v for k, v in per_block.items() if k > 0}
        over = {k: v for k, v in named_blocks.items() if v > RUBRIC_POSITIVE_CAP}
        if over:
            over_cap = True
            cap_detail = f"block(s) exceed {RUBRIC_POSITIVE_CAP} positive pts: {over}"
    elif total > RUBRIC_POSITIVE_CAP:
        over_cap = True
        cap_detail = (
            f"positive total {total} exceeds {RUBRIC_POSITIVE_CAP} max for non-milestone"
        )

    return RubricPositiveAnalysis(
        total_positive_pts=total,
        positive_line_count=line_count,
        per_block_positive_pts=per_block,
        rubric_text=text,
        rubric_source=rubric_source,
        num_milestones=num_milestones,
        over_cap=over_cap,
        cap_detail=cap_detail,
        found=True,
    )


def _extract_trailing_agent_rubric(text: str) -> str:
    """Platform rubric often appears as trailing Agent lines after test-quality review."""
    lines = text.splitlines()
    collected: list[str] = []
    for line in reversed(lines):
        stripped = line.strip()
        if AGENT_LINE_RE.match(stripped):
            collected.insert(0, stripped)
        elif collected:
            break
    return "\n".join(collected) if len(collected) >= 3 else ""


def extract_rubric_text_from_report(report_text: str) -> tuple[str | None, str]:
    """Pull platform rubric body from a submission export (e.g. entire-report.txt).

    Returns ``(rubric_text_or_none, source_label)``.
    """
    if not report_text.strip():
        return None, ""

    lines = report_text.splitlines()

    # Explicit "Agent-generated rubric" section
    for i, line in enumerate(lines):
        if _EXPORT_RUBRIC_MARKER.match(line.strip()):
            chunk = "\n".join(lines[i + 1 :]).strip()
            if re.search(r"^Agent ", chunk, re.M) or RUBRIC_HEADER_RE.search(chunk):
                return chunk, "Agent-generated rubric section"

    # First # Rubric N header through end of file
    for i, line in enumerate(lines):
        if RUBRIC_HEADER_RE.match(line.strip()):
            block = "\n".join(lines[i:]).strip()
            if re.search(r"^Agent ", block, re.M):
                return block, "# Rubric N section"

    trailing = _extract_trailing_agent_rubric(report_text)
    if trailing:
        return trailing, "trailing Agent lines"

    agent_lines = [ln.strip() for ln in lines if AGENT_LINE_RE.match(ln.strip())]
    if len(agent_lines) >= 3:
        return "\n".join(agent_lines), "Agent lines in report"

    return None, ""


def positive_points_from_entire_report(
    report_path: Path | str,
    *,
    num_milestones: int | None = None,
) -> RubricPositiveAnalysis:
    """Read entire-report (or any submission export) and sum positive rubric points only."""
    path = Path(report_path)
    if not path.is_file():
        return RubricPositiveAnalysis(
            rubric_source=str(path),
            cap_detail="report file not found",
        )

    report_text = path.read_text(encoding="utf-8", errors="replace")
    rubric_text, label = extract_rubric_text_from_report(report_text)
    source = f"{path.name}" + (f" ({label})" if label else "")

    if rubric_text is None:
        return RubricPositiveAnalysis(rubric_source=source)

    n_ms = num_milestones if num_milestones is not None else 0
    return analyze_rubric_positives(
        rubric_text,
        num_milestones=n_ms,
        rubric_source=source,
    )


def positive_points_from_rubric_text(
    rubric_text: str,
    *,
    num_milestones: int = 0,
    rubric_source: str = "rubric text",
) -> RubricPositiveAnalysis:
    """Sum positive points from raw rubric text (e.g. rubric.txt or --rubric)."""
    return analyze_rubric_positives(
        rubric_text,
        num_milestones=num_milestones,
        rubric_source=rubric_source,
    )


def main() -> int:
    """CLI: sum positive rubric points from entire-report.txt or rubric file."""
    parser = argparse.ArgumentParser(
        description="Sum positive rubric points (+lines only) from a submission export or rubric file",
    )
    parser.add_argument("path", type=Path, help="entire-report.txt or rubric.txt")
    parser.add_argument("--milestones", type=int, default=0, help="number_of_milestones from task.toml")
    args = parser.parse_args()

    path = args.path
    if path.name.lower().startswith("entire") or "report" in path.name.lower():
        analysis = positive_points_from_entire_report(path, num_milestones=args.milestones)
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        analysis = positive_points_from_rubric_text(
            text,
            num_milestones=args.milestones,
            rubric_source=str(path),
        )

    if not analysis.found:
        print(f"No rubric found in {path}")
        return 1

    print(f"Source: {analysis.rubric_source}")
    print(f"Positive point total: {analysis.total_positive_pts}")
    print(f"Positive line count: {analysis.positive_line_count}")
    print(f"Cap: {RUBRIC_POSITIVE_CAP} (blocker only if >{RUBRIC_POSITIVE_CAP})")
    print(f"Status: {analysis.cap_status}")
    if analysis.per_block_positive_pts:
        print(f"Per block: {analysis.per_block_positive_pts}")
    if analysis.over_cap:
        print(f"BLOCKER: {analysis.cap_detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
