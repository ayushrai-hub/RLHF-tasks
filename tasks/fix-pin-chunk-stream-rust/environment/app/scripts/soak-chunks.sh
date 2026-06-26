#!/usr/bin/env bash
set -euo pipefail

cd /app
export PATH="/usr/local/cargo/bin:${PATH}"

TRACES="${STREAM_TRACES:-/app/data/traces}"
OUT_DIR="/app/data/replay_out"
CATALOG="${OUT_DIR}/catalog.json"
STAMP="${OUT_DIR}/.soak-stamp"

mkdir -p "${OUT_DIR}"
rm -f "${STAMP}"

bash /app/scripts/replay-chunks.sh
cp "${CATALOG}" "${OUT_DIR}/catalog.pass1.json"
rm -f "${CATALOG}"
bash /app/scripts/replay-chunks.sh
cp "${CATALOG}" "${OUT_DIR}/catalog.pass2.json"

python3 <<'PY'
import json
from pathlib import Path

out = Path("/app/data/replay_out")
first = json.loads((out / "catalog.pass1.json").read_text())
second = json.loads((out / "catalog.pass2.json").read_text())
if first != second:
    raise SystemExit("soak-chunks: catalog export differed between passes")
(out / ".soak-stamp").write_text("ok\n")
print(f"soak-chunks: stable catalog across two passes ({len(first)} schedules)")
PY
