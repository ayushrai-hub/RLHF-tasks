"""Subprocess helpers for love letter preservation tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=merged,
        capture_output=True,
        text=True,
    )


def run_checked(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    proc = run(cmd, **kwargs)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return proc
