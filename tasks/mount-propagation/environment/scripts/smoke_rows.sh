#!/bin/sh
set -eu
slug="${1:-mp_control}"
ctl_r7 --scenario "$slug" >/dev/null 2>&1 || exit 1
python3 - <<'PY'
import json
from pathlib import Path
record = json.loads(Path("/app/output/r7_matrix_record.json").read_text())
assert record.get("rows"), "rows present"
print("smoke ok")
PY
