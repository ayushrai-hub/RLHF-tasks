#!/bin/bash
set -euo pipefail

cat > /app/scripts/build_audit.py <<'EOF'
#!/usr/bin/env python3
"""Replay touch sequence and emit Ninja rebuild audit JSON."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

APP = Path("/app")
BUILD = APP / "build"
NINJA_LOG = BUILD / ".ninja_log"
DEFAULT_FIXTURE = APP / "fixtures" / "touch_order.json"
DEFAULT_OUTPUT = APP / "output" / "build_audit.json"


def _load_fixture(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fixture must be a JSON object")
    return payload


def _parse_rebuilds(log_path: Path, start_offset: int) -> list[str]:
    raw = log_path.read_bytes()
    chunk = raw[start_offset:].decode("utf-8", errors="replace")
    rebuilt: list[str] = []
    for line in chunk.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        if parts[0] == parts[1]:
            continue
        rebuilt.append(parts[3].strip())
    return rebuilt


def _touch(path: Path, token: str) -> None:
    path.write_text(
        path.read_text(encoding="utf-8") + f"\n// depfix-touch-token={token}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not str(args.fixture).startswith("/"):
        print("fixture path must be absolute", file=sys.stderr)
        return 2
    if not str(args.output).startswith("/"):
        print("output path must be absolute", file=sys.stderr)
        return 2

    fixture = _load_fixture(args.fixture)
    entries = fixture.get("touch_entries", [])
    if not isinstance(entries, list):
        print("touch_entries must be a list", file=sys.stderr)
        return 2

    all_rebuilt: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            print("touch_entries items must be objects", file=sys.stderr)
            return 2
        path = Path(str(entry.get("path", "")))
        token = str(entry.get("token", ""))
        if not path.is_file():
            print(f"missing touch path: {path}", file=sys.stderr)
            return 2
        offset = NINJA_LOG.stat().st_size if NINJA_LOG.exists() else 0
        _touch(path, token)
        proc = subprocess.run(
            ["ninja", "-C", str(BUILD)],
            cwd=str(APP),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            return proc.returncode
        for item in _parse_rebuilds(NINJA_LOG, offset):
            if item in seen:
                continue
            seen.add(item)
            all_rebuilt.append(item)

    report = {
        "schema_version": 1,
        "workload_id": str(fixture.get("workload_id", "unknown")),
        "touch_count": len(entries),
        "rebuilt_targets": sorted(all_rebuilt),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF

chmod +x /app/scripts/build_audit.py
