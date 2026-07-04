#!/bin/bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

cp "${ROOT_DIR}/files/codec/crc.go" /app/environment/internal/codec/crc.go
cp "${ROOT_DIR}/files/scan/load.go" /app/environment/internal/scan/load.go
cp "${ROOT_DIR}/files/chain/link.go" /app/environment/internal/chain/link.go
cp "${ROOT_DIR}/files/seal/tip.go" /app/environment/internal/seal/tip.go
cp "${ROOT_DIR}/files/audit/engine.go" /app/environment/internal/audit/engine.go

bash -lc 'go build -C /app/environment -o /app/bin/registeraudit /app/environment/cmd/registeraudit'

mkdir -p /app/out
/opt/verifier-venv/bin/python3 <<'PY'
import json
import subprocess
from pathlib import Path

app = Path("/app")
bin_path = app / "bin" / "registeraudit"
practice = app / "environment" / "fixtures" / "practice"
out = app / "out" / "mreg_audit.json"

subprocess.run(
    [
        str(bin_path),
        "audit",
        "-mreg-dir",
        str(practice),
        "-segment",
        "3",
        "-json-out",
        str(out),
    ],
    check=True,
)

report = json.loads(out.read_text(encoding="utf-8"))
if "debug" in report:
    raise SystemExit("report must be flat JSON")
if report.get("register_read_count", 0) < 3:
    raise SystemExit("register read count too low")
if not (app / "out" / ".mregtip").is_file():
    raise SystemExit("tip not persisted")
PY
