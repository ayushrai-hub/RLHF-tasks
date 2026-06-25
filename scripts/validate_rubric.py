#!/usr/bin/env python3
"""Validate Terminus rubric format per Edition 2 CI rules."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ALLOWED_SCORES = {1, 2, 3, 5}
CRITERION_RE = re.compile(r"^Agent .+, [+-](\d+)\s*$")
HEADER_RE = re.compile(r"^# Rubric (\d+)\s*$")


def validate_rubric(text: str, expect_milestones: int | None = None) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []
    negatives = 0
    positives = 0
    rubric_blocks: dict[int, int] = {}
    current_rubric = 0
    non_empty_lines = [ln.rstrip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#") or ln.strip().startswith("# Rubric")]

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        hm = HEADER_RE.match(line)
        if hm:
            current_rubric = int(hm.group(1))
            rubric_blocks.setdefault(current_rubric, 0)
            continue
        if line.startswith("#") and not line.startswith("# Rubric"):
            continue
        if not line.startswith("Agent"):
            if line:
                warnings.append(f"Non-criterion line (ignored): {line[:60]}")
            continue
        m = CRITERION_RE.match(line)
        if not m:
            errors.append(f"Invalid format (must be 'Agent ..., ±N'): {line[:80]}")
            continue
        score = int(m.group(1))
        sign = "-" if ", -" in line else "+"
        if score not in ALLOWED_SCORES:
            errors.append(f"Forbidden score {sign}{score} (use ±1,2,3,5): {line[:80]}")
        if sign == "-":
            negatives += 1
        else:
            positives += 1
            if current_rubric:
                rubric_blocks[current_rubric] = rubric_blocks.get(current_rubric, 0) + score

    if negatives < 3:
        errors.append(f"Need ≥3 negative criteria (found {negatives})")

    if expect_milestones and expect_milestones > 0:
        if len(rubric_blocks) < expect_milestones:
            errors.append(f"Expected {expect_milestones} '# Rubric N' blocks (found {len(rubric_blocks)})")
        for n, pts in rubric_blocks.items():
            if pts < 10 or pts > 40:
                warnings.append(f"Rubric {n}: {pts} positive pts (target 10–40 per milestone)")
    elif not rubric_blocks and positives > 0:
        if positives < 10 or positives > 40:
            warnings.append(f"Non-milestone: {positives} positive pts (target 10–40 total)")

    return errors + [f"WARNING: {w}" for w in warnings]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Terminus rubric format")
    parser.add_argument("rubric_file", type=Path)
    parser.add_argument("--milestones", type=int, default=0, help="Expected milestone count")
    args = parser.parse_args()

    if not args.rubric_file.exists():
        print(f"ERROR: File not found: {args.rubric_file}")
        return 1

    text = args.rubric_file.read_text(encoding="utf-8")
    issues = validate_rubric(text, args.milestones or None)
    errors = [i for i in issues if not i.startswith("WARNING:")]
    warnings = [i for i in issues if i.startswith("WARNING:")]

    for i in issues:
        print(i)
    print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
