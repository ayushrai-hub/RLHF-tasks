#!/usr/bin/env bash
set -eu

prefix=${1:?install prefix required}
manifest=${2:?manifest path required}
ledger=${3:?ledger path required}

if [ ! -f "$manifest" ]; then
  echo "missing manifest: $manifest" >&2
  exit 2
fi

python3 - <<'PY' "$manifest" "$ledger"
import json, sys
manifest_path, ledger_path = sys.argv[1:3]
with open(manifest_path, encoding="utf-8") as handle:
    manifest = json.load(handle)
if not ledger_path:
    raise SystemExit(0)
try:
    with open(ledger_path, encoding="utf-8") as handle:
        ledger = json.load(handle)
except FileNotFoundError:
    raise SystemExit(0)
if manifest.get("ledger", {}).get("generation") != ledger.get("generation"):
    raise SystemExit(4)
PY

tree_root=$(python3 - <<'PY' "$manifest"
import hashlib, json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    manifest = json.load(handle)
lines = [f"{entry['path']}:{entry['sha256']}" for entry in manifest["tree"]]
lines.sort()
digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
print(digest)
PY
)

recorded=$(python3 - <<'PY' "$manifest"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    manifest = json.load(handle)
print(manifest.get("ledger", {}).get("tree_root_sha256", ""))
PY
)

if [ "$tree_root" != "$recorded" ]; then
  exit 5
fi
