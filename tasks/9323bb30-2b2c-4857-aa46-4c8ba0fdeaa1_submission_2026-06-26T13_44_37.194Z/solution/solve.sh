#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/scala3/bin:/app/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="/app/src/main/scala/vaultshard"

echo "Reading normative contracts..."
head -n 8 /app/docs/vshard-frame-format.md /app/docs/material-precedence.md /app/docs/audit-report-schema.md

echo "Inspecting broken ingest/export sources..."
grep -n "ORDER BY\|setAutoCommit\|sourceRank\|System.current" \
  "${DST}/Store.scala" "${DST}/Ingest.scala" "${DST}/Replay.scala" "${DST}/Export.scala" || true

echo "Oracle fixed modules:"
ls -la "${SCRIPT_DIR}/fixed/"

cp "${SCRIPT_DIR}/fixed/Ingest.scala" "${DST}/Ingest.scala"
cp "${SCRIPT_DIR}/fixed/Replay.scala" "${DST}/Replay.scala"
cp "${SCRIPT_DIR}/fixed/Export.scala" "${DST}/Export.scala"
cp "${SCRIPT_DIR}/fixed/Store.scala" "${DST}/Store.scala"

/app/scripts/build.sh

mkdir -p /app/data /app/output
rm -f /app/data/vault.db
/app/bin/vaultshard-ingest --db /app/data/vault.db --bundle /app/fixtures/public/sample_bundle.vshard
/app/bin/vaultshard-export --db /app/data/vault.db --tenant-id TENANT-ALPHA --out /app/output/vault-hotreload-audit.json
