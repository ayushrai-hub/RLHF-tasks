#!/usr/bin/env python3
"""Generate tasks/README.md index from task.toml metadata."""

from __future__ import annotations

import re
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

    lines = [
        "# Terminus Tasks Index",
        "",
        f"_Auto-generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_ — run `./scripts/reorganize-tasks.sh` to refresh.",
        "",
        "| Task | Difficulty | Category | Layout | Review |",
        "|------|------------|----------|--------|--------|",
    ]
    for name, diff, cat, layout, status in rows:
        lines.append(f"| `{name}` | {diff} | {cat} | {layout} | {status} |")

    lines.extend(
        [
            "",
            "## Layout",
            "",
            "- **Active tasks:** this directory (`tasks/<name>/`)",
            "- **Submission ZIPs:** `_incoming/zips/`",
            "- **External review reports:** `reviews/`",
            "- **Duplicate copies:** `_backup/copies/`",
            "- **Personal / unrelated files:** `_misc/personal/`",
            "",
            "## Commands",
            "",
            "```bash",
            "./scripts/terminus validate tasks/<name>",
            "./scripts/terminus review tasks/<name> --report reviews/entire-report.txt",
            "./scripts/terminus check-all tasks/<name>",
            "```",
            "",
        ]
    )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO_ROOT)} ({len(rows)} tasks)")


if __name__ == "__main__":
    main()
