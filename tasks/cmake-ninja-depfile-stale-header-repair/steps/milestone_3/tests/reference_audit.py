"""Independent audit replay helpers for milestone 3 verification."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

APP = Path("/app")
BUILD = APP / "build"
NINJA_LOG = BUILD / ".ninja_log"


def parse_ninja_log_rebuilds(log_path: Path, start_offset: int) -> list[str]:
    """Verbatim column-4 paths after offset; drop only exact duplicate spellings."""
    raw = log_path.read_bytes()
    chunk = raw[start_offset:].decode("utf-8", errors="replace")
    rebuilt: list[str] = []
    seen: set[str] = set()
    for line in chunk.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        if parts[0] == parts[1]:
            continue
        item = parts[3].strip()
        if item in seen:
            continue
        seen.add(item)
        rebuilt.append(item)
    return rebuilt


def expected_rebuilt_after_offset(start_offset: int) -> list[str]:
    """Sorted rebuilt targets that must appear in the log after start_offset."""
    return sorted(parse_ninja_log_rebuilds(NINJA_LOG, start_offset))


def load_fixture(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fixture must be a JSON object")
    return payload


def touch_with_token(path: Path, token: str) -> None:
    path.write_text(
        path.read_text(encoding="utf-8") + f"\n// depfix-touch-token={token}\n",
        encoding="utf-8",
    )


def reference_replay_fixture(fixture: dict) -> list[str]:
    """Replay fixture touches with per-entry offsets; merge and sort rebuilt paths."""
    entries = fixture.get("touch_entries", [])
    if not isinstance(entries, list):
        raise ValueError("touch_entries must be a list")

    merged: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("touch_entries items must be objects")
        path = Path(str(entry.get("path", "")))
        token = str(entry.get("token", ""))
        if not path.is_file():
            raise FileNotFoundError(path)
        offset = NINJA_LOG.stat().st_size if NINJA_LOG.exists() else 0
        touch_with_token(path, token)
        proc = subprocess.run(
            ["ninja", "-C", str(BUILD)],
            cwd=str(APP),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)
        for item in parse_ninja_log_rebuilds(NINJA_LOG, offset):
            if item in seen:
                continue
            seen.add(item)
            merged.append(item)
    return sorted(merged)
