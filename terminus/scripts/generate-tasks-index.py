#!/usr/bin/env python3
"""Generate tasks/README.md index from task.toml metadata."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from pathlib import Path

TERM_HUB = Path(__file__).resolve().parent.parent
REPO_ROOT = TERM_HUB.parent
TASKS = REPO_ROOT / "tasks"
OUT = TASKS / "README.md"

SKIP = {"law-samples", "README.md"}


def read_toml_field(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}\s*=\s*\"([^\"]*)\"", text, re.M)
    return m.group(1) if m else ""


def review_status(task_dir: Path) -> str:
    report = task_dir / "review-report.md"
    if not report.exists() or report.stat().st_size < 50:
        return "—"
    head = report.read_text(encoding="utf-8", errors="replace")[:2000]
    for label in ("Accept", "Revise", "Decline"):
        if f"**Disposition** | {label}" in head or f"**Disposition:** {label}" in head:
            return label
        if f"Disposition** | {label}" in head:
            return label
        if f"**Recommendation:** {label}" in head:
            return label
    return "reviewed"


def main() -> None:
    rows: list[tuple[str, str, str, str, str]] = []

    for path in sorted(TASKS.iterdir()):
        if not path.is_dir() or path.name in SKIP:
            continue
        toml = path / "task.toml"
        if not toml.exists():
            continue
        text = toml.read_text(encoding="utf-8", errors="replace")
        difficulty = read_toml_field(text, "difficulty") or "—"
        category = read_toml_field(text, "category") or "—"
        milestones = re.search(r"number_of_milestones\s*=\s*(\d+)", text)
        layout = "milestone" if milestones and int(milestones.group(1)) > 0 else "regular"
        rows.append((path.name, difficulty, category, layout, review_status(path)))

    n = len(rows)
    by_layout = Counter(r[3] for r in rows)
    by_diff = Counter(r[1] for r in rows)
    by_review = Counter(r[4] for r in rows)
    by_cat = Counter(r[2] for r in rows).most_common(6)

    lines = [
        "# Terminus Tasks Library",
        "",
        f"**{n} tasks** in this directory — Harbor benchmark tasks for Project Terminus Edition 2.",
        "",
        f"_Index auto-generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_ · refresh with `./scripts/reorganize-tasks.sh`",
        "",
        "## At a glance",
        "",
        "| Metric | Count |",
        "|--------|------:|",
        f"| Total tasks | {n} |",
        f"| Regular layout | {by_layout.get('regular', 0)} |",
        f"| Milestone layout | {by_layout.get('milestone', 0)} |",
        f"| Review: Accept | {by_review.get('Accept', 0)} |",
        f"| Review: Revise | {by_review.get('Revise', 0)} |",
        f"| Review: not yet reviewed | {by_review.get('—', 0)} |",
        "",
        "**Difficulty:** "
        + ", ".join(f"{k} {v}" for k, v in sorted(by_diff.items(), key=lambda x: -x[1])),
        "",
        "**Top categories:** "
        + ", ".join(f"{k} ({v})" for k, v in by_cat),
        "",
        "## Finding a task",
        "",
        "- Browse the table below (sorted alphabetically)",
        "- Search by folder name: `ls tasks | rg stellar`",
        "- UUID-stub names (e.g. `00af3d22-15f-task`) need `metadata.name` in `task.toml` for canonical renaming",
        "",
        "## Per-task structure",
        "",
        "```",
        "tasks/<name>/",
        "├── instruction.md      # Agent prompt",
        "├── task.toml           # Metadata, timeouts, category",
        "├── environment/        # Dockerfile + app code (no solution/tests)",
        "├── solution/solve.sh   # Oracle (not visible to agent)",
        "├── tests/              # Verifiers (not in Docker image)",
        "├── review-report.md    # Portal review (if reviewed)",
        "└── audit-report.md     # 55-item audit (if run)",
        "```",
        "",
        "## Commands",
        "",
        "```bash",
        "./scripts/terminus validate tasks/<name>",
        "./scripts/terminus check-all tasks/<name>",
        "./scripts/terminus review tasks/<name> --report terminus/reviews/entire-report.txt",
        "./scripts/terminus oracle tasks/<name>",
        "./scripts/terminus agent tasks/<name> --model gpt-5.5 --runs 3",
        "```",
        "",
        "## Full index",
        "",
        "| Task | Difficulty | Category | Layout | Review |",
        "|------|------------|----------|--------|--------|",
    ]
    for name, diff, cat, layout, status in rows:
        lines.append(f"| `{name}` | {diff} | {cat} | {layout} | {status} |")

    lines.extend(
        [
            "",
            "## Related paths",
            "",
            "| Path | Contents |",
            "|------|----------|",
            "| [`jobs/`](../jobs/) | Harbor oracle/agent run logs |",
            "| [`terminus/reviews/`](../terminus/reviews/) | Platform submission exports |",
            "| [`terminus/_incoming/zips/`](../terminus/_incoming/zips/) | Archived submission ZIPs |",
            "| [`terminus/_backup/copies/`](../terminus/_backup/copies/) | Duplicate task folders |",
            "",
        ]
    )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO_ROOT)} ({len(rows)} tasks)")


if __name__ == "__main__":
    main()
