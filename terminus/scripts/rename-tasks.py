#!/usr/bin/env python3
"""Rename UUID/submission task folders to canonical slugs; dedupe; extract zips."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

TERM_HUB = Path(__file__).resolve().parent.parent
REPO_ROOT = TERM_HUB.parent
TASKS = REPO_ROOT / "tasks"
BACKUP = TERM_HUB / "_backup" / "copies"
INCOMING = TERM_HUB / "_incoming" / "zips"

UUID_SUBMISSION = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f-]+_submission_\d{4}-\d{2}-\d{2}T[\d_.]+Z(?: \d+)?$"
)

# Explicit UUID → canonical slug (when task.toml lacks metadata.name)
UUID_MAP = {
    "21db18f7-045f-42d8-8f80-7fe70f2def24_submission_2026-06-29T09_17_14.785Z": "block_sealed_export_wal",
    "40e57f12-6376-4580-b652-323845c350bb_submission_2026-06-27T05_30_48.973Z": "diffusion-workbook-import",
    "5b1a670c-a989-4f9d-ae60-eeff3a2a466f_submission_2026-06-29T12_34_55.358Z": "repair-ruby-jws-skew-audits-rack-api",
    "78d6ce16-a329-4312-8582-d329bf0f90f4_submission_2026-07-03T13_44_04.578Z": "raft-consensus-recovery",
    "99d29fdd-b549-4989-a2e3-f39def9b2dd1_submission_2026-07-03T08_58_51.781Z": "initramfs-reachability-budget",
    "ecacd7da-f89d-4706-9705-ba07177f1740_submission_2026-06-28T11_13_50.186Z": "hive-scale-replay-rollups",
    "f2fed125-8b22-4c25-9569-74a1724ab3af_submission_2026-07-03T11_59_32.391Z": "rbac-temporal-rust",
    "8e1ce3ea-8aa0-40e4-9fe0-d73c7ca51a32-submission-2026-06-28t09-08-09-627z-copy": "metrics-aggregator",
}

# Other misnamed folders → canonical slug
MANUAL_RENAMES = {
    "download": "msreport-isotope-envelopes",
    "rbac_temporal_rust_task_submission_ready": "rbac-temporal-rust",
    "zipawk-exhibit-signature-policy-audit": "awk-exhibit-signature-policy-audit",
    "routenet-tbench-submission": "routenet-tbench",
    "gsqt-importable-config-training-submission-21": "gsqt-importable-config-training",
}

SKIP_NAMES = {
    "README.md",
    "law-samples",
    "terminus",
    "docs",
    "scripts",
    "templates",
    "jobs",
}


def read_toml_name(task_dir: Path) -> str:
    toml = task_dir / "task.toml"
    if not toml.is_file():
        return ""
    text = toml.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.M)
    if m and not m.group(1).startswith("milestone_"):
        return m.group(1).strip()
    return ""


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "unnamed-task"


def is_task_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / "task.toml").is_file():
        return True
    if (path / "instruction.md").is_file() and (path / "environment").is_dir():
        return True
    if (path / "steps" / "milestone_1" / "instruction.md").is_file():
        return True
    return False


def task_file_set(root: Path) -> set[str]:
    """Relative paths excluding review/audit noise for duplicate detection."""
    skip = {".cursor", "__MACOSX", ".step2b-metrics.jsonl", ".gitignore"}
    out: set[str] = set()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in skip for part in rel.parts):
            continue
        if rel.name in ("audit-report.md", "review-report.md"):
            continue
        out.add(str(rel))
    return out


def file_contents_equal(a: Path, b: Path) -> bool:
    try:
        return a.read_bytes() == b.read_bytes()
    except OSError:
        return False


def trees_equivalent(a: Path, b: Path) -> bool:
    fa, fb = task_file_set(a), task_file_set(b)
    if fa != fb:
        return False
    for rel in fa:
        if not file_contents_equal(a / rel, b / rel):
            return False
    return True


def archive_existing(dest: Path, reason: str) -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    target = BACKUP / dest.name
    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(dest), str(target))
    print(f"ARCHIVED existing {dest.name} -> _backup/copies/ ({reason})")


def merge_review_artifacts(src: Path, dest: Path) -> None:
    for fname in ("review-report.md", "audit-report.md"):
        s, d = src / fname, dest / fname
        if s.is_file() and (not d.is_file() or d.stat().st_size < s.stat().st_size):
            shutil.copy2(s, d)


def canonical_name_for(path: Path) -> str | None:
    base = path.name
    if base in UUID_MAP:
        return UUID_MAP[base]
    if UUID_SUBMISSION.match(base):
        meta = read_toml_name(path)
        if meta:
            return slugify(meta)
        return slugify(base.split("_submission_")[0][:12] + "-task")
    if base in MANUAL_RENAMES:
        return MANUAL_RENAMES[base]
    if base.endswith(".") and base != ".":
        return base.rstrip(".")
    if "_submission_" in base and not UUID_SUBMISSION.match(base):
        stem = base.split("_submission")[0]
        if stem:
            return slugify(stem)
    return None


def rename_task(src: Path, dest_name: str) -> None:
    dest = TASKS / dest_name
    if src.resolve() == dest.resolve():
        return
    if dest.exists():
        if trees_equivalent(src, dest):
            merge_review_artifacts(src, dest)
            shutil.rmtree(src)
            print(f"DEDUPED (identical): removed {src.name} -> kept {dest_name}")
            return
        archive_existing(dest, f"replaced by {src.name}")
    print(f"RENAME: {src.name} -> {dest_name}")
    shutil.move(str(src), str(dest))


def strip_trailing_dots() -> None:
    for entry in sorted(TASKS.iterdir()):
        if not entry.is_dir() or entry.name in SKIP_NAMES:
            continue
        if entry.name.endswith("."):
            rename_task(entry, entry.name.rstrip("."))


def extract_all_zips() -> None:
    zips = sorted(
        p
        for p in REPO_ROOT.rglob("*.zip")
        if ".git" not in p.parts and "node_modules" not in p.parts
    )
    for zp in zips:
        stem = zp.stem.strip()
        dest = TASKS / stem
        if dest.is_dir() and is_task_dir(dest):
            zp.unlink(missing_ok=True)
            print(f"DELETE zip (task exists): {zp.relative_to(REPO_ROOT)}")
            continue
        with tempfile.TemporaryDirectory(prefix="terminus-rename-") as tmp:
            tmp_path = Path(tmp)
            with zipfile.ZipFile(zp) as zf:
                zf.extractall(tmp_path)
            # find task root
            candidates = [tmp_path]
            candidates.extend(p for p in tmp_path.iterdir() if p.is_dir() and p.name != "__MACOSX")
            task_root = next((p for p in candidates if is_task_dir(p)), None)
            if task_root is None:
                for p in tmp_path.rglob("task.toml"):
                    task_root = p.parent
                    break
            if task_root is None or not is_task_dir(task_root):
                print(f"SKIP zip (not a task): {zp.relative_to(REPO_ROOT)}")
                continue
            canonical = read_toml_name(task_root) or stem
            canonical = slugify(canonical) if canonical else slugify(stem.split("_submission")[0])
            if UUID_MAP.get(stem):
                canonical = UUID_MAP[stem]
            dest_path = TASKS / canonical
            if dest_path.exists():
                if trees_equivalent(task_root, dest_path):
                    print(f"SKIP zip duplicate: {zp.name}")
                else:
                    archive_existing(dest_path, f"from zip {zp.name}")
                    shutil.copytree(task_root, dest_path)
                    print(f"EXTRACT replace: {zp.name} -> {canonical}")
            else:
                shutil.copytree(task_root, dest_path)
                print(f"EXTRACT: {zp.name} -> {canonical}")
            zp.unlink(missing_ok=True)


def main() -> int:
    TASKS.mkdir(parents=True, exist_ok=True)
    extract_all_zips()

    # UUID and manual renames first (long names before dot stripping)
    for entry in sorted(TASKS.iterdir(), key=lambda p: len(p.name), reverse=True):
        if not entry.is_dir() or entry.name in SKIP_NAMES:
            continue
        target = canonical_name_for(entry)
        if target and target != entry.name:
            rename_task(entry, target)

    strip_trailing_dots()

    idx = TERM_HUB / "scripts" / "generate-tasks-index.py"
    if idx.is_file():
        subprocess.run([sys.executable, str(idx)], check=False, cwd=REPO_ROOT)

    remaining_uuid = [
        p.name for p in TASKS.iterdir() if p.is_dir() and UUID_SUBMISSION.match(p.name)
    ]
    zips_left = list(REPO_ROOT.rglob("*.zip"))
    print(f"\nUUID folders remaining: {len(remaining_uuid)}")
    for n in remaining_uuid:
        print(f"  {n}")
    print(f"Zips remaining: {len(zips_left)}")
    return 1 if remaining_uuid else 0


if __name__ == "__main__":
    raise SystemExit(main())
