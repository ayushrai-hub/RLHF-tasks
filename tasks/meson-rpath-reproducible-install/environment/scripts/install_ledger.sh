#!/usr/bin/env bash
set -eu

ledger_path=${1:?ledger path required}
pipeline_mode=${2:?pipeline mode required}
manifest_path=${3:?manifest path required}
catalog_epoch=${4:?catalog epoch required}

manifest_sha=$(sha256sum "$manifest_path" | awk '{print $1}')

if [ "$pipeline_mode" = "fresh" ]; then
  if [ -f "$ledger_path" ]; then
    generation=$(python3 - <<'PY' "$ledger_path"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(int(json.load(handle).get("generation", 0)) + 1)
PY
)
  else
    generation=1
  fi
else
  if [ ! -f "$ledger_path" ]; then
    generation=1
  else
    generation=$(python3 - <<'PY' "$ledger_path"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(int(json.load(handle).get("generation", 1)))
PY
)
  fi
fi

mkdir -p "$(dirname "$ledger_path")"
python3 - <<'PY' "$ledger_path" "$generation" "$catalog_epoch" "$manifest_sha"
import json, sys
path, generation, catalog_epoch, manifest_sha = sys.argv[1:5]
payload = {
    "schema": "capsule-install-ledger-v1",
    "generation": int(generation),
    "catalog_epoch": catalog_epoch,
    "last_manifest_sha256": manifest_sha,
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
