#!/usr/bin/env python3
"""Discover Terminus task directories under tasks/ and optional repo-root orphans."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TERM_HUB = SCRIPT_DIR.parent
REPO_ROOT = TERM_HUB.parent
TASKS_DIR = REPO_ROOT / "tasks"
SKIP_DIRS = {"law-samples", "README.md", "_incoming", "_backup", "_misc", "jobs", "terminus"}


def read_toml_field(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}\s*=\s*\"([^\"]*)\"", text, re.M)
    return m.group(1) if m else ""


def is_task_dir(path: Path) -> bool:
    return path.is_dir() and (path / "task.toml").is_file()


def discover_tasks(include_root: bool = True) -> list[Path]:
    found: dict[str, Path] = {}

    if TASKS_DIR.is_dir():
        for child in sorted(TASKS_DIR.iterdir()):
            if not child.is_dir() or child.name in SKIP_DIRS:
                continue
            if is_task_dir(child):
                found[child.name] = child.resolve()

    if include_root:
        for child in sorted(REPO_ROOT.iterdir()):
            if not child.is_dir() or child.name in SKIP_DIRS or child.name == "tasks":
                continue
            if child.name.startswith("."):
                continue
            if is_task_dir(child) and child.name not in found:
                found[child.name] = child.resolve()

    return [found[k] for k in sorted(found)]


def task_meta(path: Path) -> dict[str, str]:
    toml = path / "task.toml"
    text = toml.read_text(encoding="utf-8", errors="replace") if toml.exists() else ""
    return {
        "name": path.name,
        "path": str(path),
        "difficulty": read_toml_field(text, "difficulty"),
        "category": read_toml_field(text, "category"),
        "layout": "milestone" if (path / "steps").is_dir() else "regular",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="List Terminus task directories")
    parser.add_argument("--no-root", action="store_true", help="Only tasks/ subfolder")
    parser.add_argument("--json", action="store_true", help="Emit JSON array")
    parser.add_argument("--names-only", action="store_true", help="One name per line")
    args = parser.parse_args()

    tasks = discover_tasks(include_root=not args.no_root)

    if args.json:
        print(json.dumps([task_meta(t) for t in tasks], indent=2))
        return 0

    if args.names_only:
        for t in tasks:
            print(t.name)
        return 0

    for t in tasks:
        m = task_meta(t)
        print(f"{m['name']}\t{m['difficulty']}\t{m['category']}\t{m['layout']}\t{m['path']}")
    print(f"\n# {len(tasks)} tasks", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
