#!/usr/bin/env bash
set -euo pipefail

cd /app
export PATH="/usr/local/cargo/bin:${PATH}"

TRACES="${STREAM_TRACES:-/app/data/traces}"
OUT_DIR="/app/data/replay_out"
CATALOG="${OUT_DIR}/catalog.json"

mkdir -p "${OUT_DIR}"

if [[ -x /app/bin/streamd ]]; then
  BIN=/app/bin/streamd
else
  BIN=(cargo run --release --locked -p streamd --)
fi

python3 <<'PY'
import json
import os
import subprocess
from pathlib import Path

traces = Path(os.environ.get("STREAM_TRACES", "/app/data/traces"))
out_dir = Path("/app/data/replay_out")
catalog_path = out_dir / "catalog.json"
bin_path = Path("/app/bin/streamd")

paths = sorted(traces.rglob("*.trace"))
if len(paths) < 5:
    raise SystemExit(f"expected at least five trace files under {traces}")

catalog = {}
for path in paths:
    rel = path.relative_to(traces).as_posix()
    if bin_path.is_file():
        proc = subprocess.run(
            [str(bin_path), "replay-one", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        proc = subprocess.run(
            ["cargo", "run", "--release", "--locked", "-p", "streamd", "--", "replay-one", str(path)],
            check=True,
            capture_output=True,
            text=True,
            cwd="/app",
        )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    catalog[rel] = lines

catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n")
print(f"replay-chunks: wrote {catalog_path} ({len(catalog)} schedules)")
PY
