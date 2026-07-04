#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" "$2" "$3" "$4" "$5" "$6" "$7" <<'PY'
import hashlib, json, sys
snap, pool, rollup, ledger, staging, run_seq, out = sys.argv[1:8]
body = {
    "schema_version": 1,
    "collection_snapshot_hash": snap,
    "redundancy_hash": pool,
    "rollup_hash": rollup,
    "index_digest": ledger,
    "schedule_hash": staging,
    "run_sequence": int(run_seq),
    "ingest_complete": True,
}
body["manifest_hash"] = hashlib.sha256(
    json.dumps({k: body[k] for k in body if k != "manifest_hash"}, separators=(",", ":"), sort_keys=True).encode()
).hexdigest()
open(out, "w").write(json.dumps(body, indent=2) + "\n")
PY
