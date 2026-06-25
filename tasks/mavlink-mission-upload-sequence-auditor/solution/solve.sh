#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:/app/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "${SCRIPT_DIR}/fixed/crc.rs" /app/src/crc.rs
cp "${SCRIPT_DIR}/fixed/store.rs" /app/src/store.rs
cp "${SCRIPT_DIR}/fixed/ingest/mod.rs" /app/src/ingest/mod.rs
cp "${SCRIPT_DIR}/fixed/ingest/parser.rs" /app/src/ingest/parser.rs
cp "${SCRIPT_DIR}/fixed/export.rs" /app/src/export.rs

/app/scripts/oracle-build.sh

DB=/tmp/oracle-mission.db
rm -f "${DB}"
export MISSION_EPOCH_BASE=1704067200

/app/bin/mission-ingest --db "${DB}" --log /app/data/sample-alpha.mseq --upload-id alpha-01 --vehicle V1
/app/bin/mission-export --db "${DB}" --vehicle V1 --upload-id alpha-01 --out /app/output/mission-report.json
test -s /app/output/mission-report.json
