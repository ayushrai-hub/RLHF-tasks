#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_ROOT="/app/environment"

find "$ENV_ROOT" -type f \( -name '*.go' -o -name '*.sh' \) -exec sed -i 's/\r$//' {} +
patch -p0 -d "$ENV_ROOT" < "$SCRIPT_DIR/oracle_clean.patch"

run_entry() {
  local entry="$1"
  bash /app/environment/scripts/start_svc.sh
  rm -rf /app/output
  mkdir -p /app/output
  cd /app/environment/infra
  terraform apply -auto-approve -var "root_entry=${entry}" -replace="null_resource.emit"
}

cd "$ENV_ROOT"
go build -o /app/environment/bin/pipeline ./cmd/pipeline

echo "== Smoke rotation across matrix entries =="
for entry in alpha beta gamma delta beta alpha; do
  echo "apply entry=$entry"
  run_entry "$entry"
  test -s /app/output/lock_snapshot.json
  test -s /app/output/checksum_rows.json
  test -s /app/output/repo_table.bzl
  test -s /app/output/module_lock.bzl
  test -s "$ENV_ROOT/.runtime/journal/replay_tail.json"
  test -s "$ENV_ROOT/.runtime/journal/replay_chain.jsonl"
done

python3 - <<'PY'
import hashlib
import json
from pathlib import Path

out = Path("/app/output")
journal = Path("/app/environment/.runtime/journal/closure.json")
tail = Path("/app/environment/.runtime/journal/replay_tail.json")
chain = Path("/app/environment/.runtime/journal/replay_chain.jsonl")
assert journal.is_file(), "closure.json missing from journal"
assert tail.is_file(), "replay_tail.json missing"
assert chain.is_file(), "replay_chain.jsonl missing"
ledger = json.loads(journal.read_text())
assert "slots" in ledger and "alpha" in ledger["slots"], "alpha slot missing"
assert ledger["slots"]["alpha"].get("pins", {}).get("mod_core") == "2.1.0"

lock = json.loads((out / "lock_snapshot.json").read_text())
checksum = json.loads((out / "checksum_rows.json").read_text())
stub = json.loads((out / "module_lock.bzl").read_text())
keys = sorted(r["repo_key"] for r in lock["rows"])
digest = {r["repo_key"]: r["digest"] for r in checksum["rows"]}
lines = [f"lock({k},{digest[k]})" for k in keys]
assert stub["lines"] == lines

payload = {"lock": lock["rows"], "checksum": checksum["rows"]}
digest_hex = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
tail_doc = json.loads(tail.read_text())
assert tail_doc["entry_id"] == "alpha"
assert tail_doc["link_digest"] == digest_hex
assert ledger["slots"]["alpha"]["link_digest"] == digest_hex
PY
echo "Oracle completed Go pipeline modules"
