#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${APP_ROOT:-/app}"
source "${APP_ROOT}/heirloom-preservation/lib/common.sh"
ensure_dirs
if [[ -f "${RUN_SEQUENCE_FILE}" ]]; then
  cur=$(python3 - "${RUN_SEQUENCE_FILE}" <<'PY'
import json,sys
print(json.load(open(sys.argv[1])).get("run_sequence",0))
PY
)
  next=$((cur+1))
else next=1
fi
python3 - "${RUN_SEQUENCE_FILE}" "$next" <<'PY'
import json,sys
open(sys.argv[1],"w").write(json.dumps({"run_sequence":int(sys.argv[2])},indent=2)+"\n")
print(sys.argv[2])
PY
