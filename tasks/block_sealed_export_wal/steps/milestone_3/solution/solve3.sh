#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="/app"

echo "== Milestone 3: load contracts =="
for doc in overview.md rotation-and-wal.md epoch-and-locks.md manifest-and-seal.md; do
  test -f "${APP}/docs/${doc}" || { echo "Missing ${APP}/docs/${doc}" >&2; exit 1; }
  echo "  contract: ${APP}/docs/${doc}"
done

echo "== Milestone 3: add rotation durability modules =="
cp "${DIR}/files/export_validator.py" "${APP}/export_validator.py"
cp "${DIR}/files/rotation_preflight.py" "${APP}/rotation_preflight.py"
cp "${DIR}/files/wal_utils.py" "${APP}/wal_utils.py"
cp "${DIR}/files/atomic_io.py" "${APP}/atomic_io.py"
cp "${DIR}/files/rotation_lock.py" "${APP}/rotation_lock.py"
cp "${DIR}/files/epoch_ledger.py" "${APP}/epoch_ledger.py"
cp "${DIR}/files/rotation_coordinator.py" "${APP}/rotation_coordinator.py"
cp "${DIR}/files/sidecar_chaining.py" "${APP}/sidecar_chaining.py"
cp "${DIR}/files/rotator.py" "${APP}/rotator.py"
cp "${DIR}/files/cli.py" "${APP}/cli.py"

echo "Milestone 3 oracle complete."
