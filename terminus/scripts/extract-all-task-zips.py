#!/usr/bin/env python3
"""Extract Terminus task zips into tasks/, validate layout, delete archives."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

TERM_HUB = Path(__file__).resolve().parent.parent
REPO_ROOT = TERM_HUB.parent
TASKS = REPO_ROOT / "tasks"
INCOMING = TERM_HUB / "_incoming" / "zips"
SUBMISSIONS = TERM_HUB / "_incoming" / "submissions"

ZIP_NAME_MAP = {
    "3a528f89-6e97-4907-a1ba-bf24238cfc77_submission_2026-06-19T10_51_41.462Z (1)": "exec-profile-cap-bound-drift",
}

SKIP_ZIP_PREFIXES = ("cropped-images", "ECG-Dataset", "law-samples")

# Never prune or treat these as tasks if they appear under tasks/
PROTECTED_TASKS_NAMES = frozenset(
    {
        "README.md",
        "terminus",
        "docs",
        "scripts",
        "templates",
        "jobs",
        ".git",
        ".cursor",
    }
)


def rescue_misplaced_hub() -> list[str]:
    """If the Terminus hub was moved under tasks/, put it back at repo root."""
    logs: list[str] = []
    misplaced = TASKS / "terminus"
    hub = REPO_ROOT / "terminus"
    if misplaced.is_dir() and not hub.exists():
        shutil.move(str(misplaced), str(hub))
        logs.append("RESCUED: tasks/terminus -> terminus/")
    elif misplaced.is_dir() and hub.exists():
        logs.append("WARN: both tasks/terminus and terminus/ exist")
    return logs


def is_terminus_task_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / "task.toml").is_file():
        return True
    if (path / "instruction.md").is_file() and (path / "environment").is_dir():
        return True
    if (path / "steps" / "milestone_1" / "instruction.md").is_file():
        return True
    return False


def task_root_in_extracted(tmp: Path) -> Path | None:
    """Find the directory that looks like a Terminus task inside an extract tree."""
    if is_terminus_task_dir(tmp):
        return tmp

    task_sub = tmp / "task"
    if is_terminus_task_dir(task_sub):
        return task_sub

    children = [p for p in tmp.iterdir() if p.is_dir() and p.name != "__MACOSX"]
    if len(children) == 1 and is_terminus_task_dir(children[0]):
        return children[0]

    for child in children:
        if is_terminus_task_dir(child):
            return child
    return None


def dest_name_for_zip(zip_path: Path) -> str:
    base = zip_path.stem.strip()
    if base in ZIP_NAME_MAP:
        return ZIP_NAME_MAP[base]
    if base.endswith("_submission"):
        return base  # keep UUID_submission for Snorkel exports
    return base


def copy_task_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def extract_zip_to_tasks(zip_path: Path) -> str:
    base = zip_path.stem.strip()
    for prefix in SKIP_ZIP_PREFIXES:
        if base.startswith(prefix):
            return f"SKIP non-task: {zip_path.name}"

    dest_name = dest_name_for_zip(zip_path)
    dest = TASKS / dest_name

    if dest.is_dir() and is_terminus_task_dir(dest):
        return f"SKIP exists: {zip_path.name} -> tasks/{dest_name}"

    with tempfile.TemporaryDirectory(prefix="terminus-zip-") as tmpdir:
        tmp = Path(tmpdir)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)

        task_root = task_root_in_extracted(tmp)
        if task_root is None:
            return f"REJECT not task format: {zip_path.name}"

        copy_task_tree(task_root, dest)

    return f"EXTRACTED: {zip_path.name} -> tasks/{dest_name}"


def promote_submission_dirs() -> list[str]:
    logs: list[str] = []
    if not SUBMISSIONS.is_dir():
        return logs

    for sub in sorted(SUBMISSIONS.iterdir()):
        if not sub.is_dir():
            continue
        task_sub = sub / "task"
        if not is_terminus_task_dir(task_sub):
            continue
        dest_name = sub.name.strip()
        dest = TASKS / dest_name
        if dest.is_dir() and is_terminus_task_dir(dest):
            logs.append(f"SKIP submission dir (exists): {sub.name}")
            continue
        copy_task_tree(task_sub, dest)
        logs.append(f"PROMOTED submission: {sub.name} -> tasks/{dest_name}")
    return logs


def prune_non_tasks() -> list[str]:
    logs: list[str] = []
    if not TASKS.is_dir():
        return logs
    for entry in sorted(TASKS.iterdir()):
        if entry.name in PROTECTED_TASKS_NAMES:
            if entry.name == "terminus" and entry.is_dir():
                logs.extend(rescue_misplaced_hub())
            continue
        if is_terminus_task_dir(entry):
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
            logs.append(f"REMOVED non-task dir: tasks/{entry.name}")
        elif entry.is_file():
            entry.unlink()
            logs.append(f"REMOVED non-task file: tasks/{entry.name}")
    return logs


def find_all_zips() -> list[Path]:
    zips: list[Path] = []
    for pattern in ("**/*.zip",):
        for p in REPO_ROOT.glob(pattern):
            if ".git" in p.parts:
                continue
            zips.append(p)
    return sorted(set(zips))


def main() -> int:
    TASKS.mkdir(parents=True, exist_ok=True)
    INCOMING.mkdir(parents=True, exist_ok=True)

    logs: list[str] = []
    logs.extend(rescue_misplaced_hub())
    logs.extend(promote_submission_dirs())

    for zip_path in find_all_zips():
        result = extract_zip_to_tasks(zip_path)
        logs.append(result)
        if result.startswith(("EXTRACTED", "SKIP exists", "SKIP non-task")):
            zip_path.unlink(missing_ok=True)
        elif result.startswith("REJECT"):
            # leave rejected zips for manual review unless in incoming (delete clutter)
            if zip_path.parent == INCOMING:
                rejected = TERM_HUB / "_incoming" / "rejected-zips"
                rejected.mkdir(parents=True, exist_ok=True)
                shutil.move(str(zip_path), str(rejected / zip_path.name))

    logs.extend(prune_non_tasks())

    # regenerate index
    idx = TERM_HUB / "scripts" / "generate-tasks-index.py"
    if idx.is_file():
        subprocess.run([sys.executable, str(idx)], check=False, cwd=REPO_ROOT)

    for line in logs:
        print(line)

    bad = [p for p in TASKS.iterdir() if p.name != "README.md" and not is_terminus_task_dir(p)]
    zips_left = find_all_zips()
    print(f"\nTasks: {sum(1 for p in TASKS.iterdir() if p.name != 'README.md' and is_terminus_task_dir(p))}")
    print(f"Non-task entries in tasks/: {len(bad)}")
    print(f"Zips remaining: {len(zips_left)}")
    for z in zips_left:
        print(f"  kept: {z.relative_to(REPO_ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
