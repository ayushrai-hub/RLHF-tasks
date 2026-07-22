#!/usr/bin/env python3
"""Parallel batch runner for Terminus validate, audit, and oracle commands."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

SCRIPT_DIR = Path(__file__).resolve().parent
TERM_HUB = SCRIPT_DIR.parent
REPO_ROOT = TERM_HUB.parent
TASKS_DIR = REPO_ROOT / "tasks"
TERMINUS_CLI = TERM_HUB / "scripts" / "terminus"
DISCOVER = SCRIPT_DIR / "discover_tasks.py"

Command = Literal["validate", "audit", "oracle", "check-all"]


@dataclass
class TaskResult:
    name: str
    path: str
    command: str
    status: Literal["pass", "fail", "error", "skip"]
    exit_code: int
    duration_sec: float
    message: str = ""
    reward: float | None = None


@dataclass
class BatchReport:
    command: str
    started_at: str
    finished_at: str
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    results: list[TaskResult] = field(default_factory=list)


def discover_task_paths(include_root: bool = True) -> list[Path]:
    cmd = [sys.executable, str(DISCOVER), "--names-only"]
    if not include_root:
        cmd.append("--no-root")
    out = subprocess.check_output(cmd, text=True, cwd=REPO_ROOT)
    names = [line.strip() for line in out.splitlines() if line.strip()]
    paths: list[Path] = []
    for name in names:
        candidate = TASKS_DIR / name
        if candidate.is_dir():
            paths.append(candidate)
            continue
        root_candidate = REPO_ROOT / name
        if root_candidate.is_dir():
            paths.append(root_candidate)
    return paths


def filter_tasks(
    tasks: list[Path],
    only: list[str] | None,
    skip: list[str] | None,
) -> list[Path]:
    if only:
        only_set = set(only)
        tasks = [t for t in tasks if t.name in only_set]
    if skip:
        skip_set = set(skip)
        tasks = [t for t in tasks if t.name not in skip_set]
    return tasks


def _read_latest_reward(task_name: str) -> float | None:
    jobs = REPO_ROOT / "jobs"
    if not jobs.is_dir():
        return None
    for job_dir in sorted(jobs.iterdir(), reverse=True):
        if not job_dir.is_dir():
            continue
        for trial in job_dir.iterdir():
            if not trial.is_dir() or not trial.name.startswith(task_name):
                continue
            reward_file = trial / "verifier" / "reward.txt"
            if reward_file.is_file():
                try:
                    return float(reward_file.read_text().strip())
                except ValueError:
                    return None
    return None


def run_one(task_path: str, command: Command, report_path: str | None) -> TaskResult:
    path = Path(task_path)
    name = path.name
    start = time.monotonic()

    if command == "oracle" and not docker_ready():
        return TaskResult(
            name=name,
            path=task_path,
            command=command,
            status="error",
            exit_code=2,
            duration_sec=time.monotonic() - start,
            message="Docker daemon not reachable",
        )

    if command == "validate":
        cmd = [sys.executable, str(SCRIPT_DIR / "validate_task.py"), task_path]
    elif command == "audit":
        cmd = [sys.executable, str(SCRIPT_DIR / "task_auditor.py"), task_path]
        if report_path:
            cmd.extend(["--report", report_path])
    elif command == "check-all":
        cmd = ["bash", str(TERMINUS_CLI), "check-all", task_path]
    else:
        harbor = shutil_which("stb") or shutil_which("harbor")
        if not harbor:
            return TaskResult(
                name=name,
                path=task_path,
                command=command,
                status="error",
                exit_code=2,
                duration_sec=time.monotonic() - start,
                message="Neither stb nor harbor found on PATH",
            )
        if harbor.endswith("stb"):
            cmd = ["stb", "harbor", "run", "-a", "oracle", "-p", task_path]
        else:
            cmd = ["harbor", "run", "-a", "oracle", "-p", task_path]

    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=900 if command == "oracle" else 120,
        )
        duration = time.monotonic() - start
        reward = _read_latest_reward(name) if command == "oracle" else None
        out_lines = (proc.stdout or "").strip().splitlines()
        msg = out_lines[-1][:240] if out_lines else ""

        if command == "oracle" and reward is not None:
            status: Literal["pass", "fail", "error", "skip"] = "pass" if reward >= 1.0 else "fail"
            if status == "fail":
                msg = msg or f"reward={reward}"
            elif proc.returncode != 0:
                msg = msg or "oracle reward=1.0 (harbor exit non-zero; likely cleanup)"
            return TaskResult(
                name=name,
                path=task_path,
                command=command,
                status=status,
                exit_code=proc.returncode,
                duration_sec=duration,
                message=msg,
                reward=reward,
            )

        if proc.returncode == 0:
            return TaskResult(
                name=name,
                path=task_path,
                command=command,
                status="pass",
                exit_code=proc.returncode,
                duration_sec=duration,
                message=msg,
                reward=reward,
            )

        err_tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        return TaskResult(
            name=name,
            path=task_path,
            command=command,
            status="fail",
            exit_code=proc.returncode,
            duration_sec=duration,
            message=" | ".join(err_tail)[:400],
            reward=reward,
        )
    except subprocess.TimeoutExpired:
        return TaskResult(
            name=name,
            path=task_path,
            command=command,
            status="error",
            exit_code=124,
            duration_sec=time.monotonic() - start,
            message="Timed out",
        )
    except Exception as exc:  # noqa: BLE001
        return TaskResult(
            name=name,
            path=task_path,
            command=command,
            status="error",
            exit_code=1,
            duration_sec=time.monotonic() - start,
            message=str(exc)[:400],
        )


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def docker_ready() -> bool:
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def print_summary(report: BatchReport) -> None:
    print(f"\n=== Batch {report.command} summary ===")
    print(f"Total: {report.total}  pass: {report.passed}  fail: {report.failed}  error: {report.errors}  skip: {report.skipped}")
    print(f"Duration window: {report.started_at} → {report.finished_at}")

    failures = [r for r in report.results if r.status in {"fail", "error"}]
    if failures:
        print("\nFailures:")
        for r in failures:
            extra = f" reward={r.reward}" if r.reward is not None else ""
            print(f"  ✗ {r.name} ({r.status}, {r.duration_sec:.1f}s){extra}: {r.message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Terminus commands across many tasks in parallel")
    parser.add_argument("command", choices=["validate", "audit", "oracle", "check-all"])
    parser.add_argument("--jobs", "-j", type=int, default=0, help="Parallel workers (default: 4 validate/audit, 1 oracle)")
    parser.add_argument("--only", nargs="*", help="Task folder names to include")
    parser.add_argument("--skip", nargs="*", help="Task folder names to exclude")
    parser.add_argument("--no-root", action="store_true", help="Only scan tasks/")
    parser.add_argument("--report", help="entire-report.txt for audit command")
    parser.add_argument("--output", "-o", help="Write JSON report path")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    args = parser.parse_args()

    command: Command = args.command
    tasks = filter_tasks(discover_task_paths(include_root=not args.no_root), args.only, args.skip)
    if not tasks:
        print("No tasks found.", file=sys.stderr)
        return 1

    default_jobs = 1 if command == "oracle" else min(4, max(1, (os.cpu_count() or 2) - 1))
    jobs = args.jobs if args.jobs > 0 else default_jobs
    if command == "oracle" and jobs > 2:
        print(f"! Capping oracle parallelism to 2 (requested {jobs})", file=sys.stderr)
        jobs = 2

    started = datetime.now(timezone.utc).isoformat()
    results: list[TaskResult] = []

    print(f"Running {command} on {len(tasks)} tasks with {jobs} worker(s)...")

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {
            pool.submit(run_one, str(t), command, args.report): t for t in tasks
        }
        for fut in as_completed(futures):
            result = fut.result()
            results.append(result)
            icon = {"pass": "✓", "fail": "✗", "error": "!", "skip": "-"}.get(result.status, "?")
            reward_s = f" reward={result.reward}" if result.reward is not None else ""
            print(f"  {icon} {result.name} ({result.duration_sec:.1f}s){reward_s}")
            if args.fail_fast and result.status != "pass":
                for pending in futures:
                    if not pending.done():
                        pending.cancel()
                break

    finished = datetime.now(timezone.utc).isoformat()
    results.sort(key=lambda r: r.name)

    report = BatchReport(
        command=command,
        started_at=started,
        finished_at=finished,
        total=len(results),
        passed=sum(1 for r in results if r.status == "pass"),
        failed=sum(1 for r in results if r.status == "fail"),
        errors=sum(1 for r in results if r.status == "error"),
        skipped=sum(1 for r in results if r.status == "skip"),
        results=results,
    )

    print_summary(report)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(report)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {out}")

    return 0 if report.failed == 0 and report.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
