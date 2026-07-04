#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${APP_ROOT:-/app}"
STATE="${APP_ROOT}/state"
OUTPUT="${APP_ROOT}/output"
COLLECTION_SNAPSHOT="${STATE}/collection-snapshot.json"
REDUNDANCY_POOLS="${STATE}/redundancy-pools.json"
MIGRATION_ROLLUP="${STATE}/migration-rollup.json"
INDEX_LEDGER="${STATE}/index-ledger.json"
PRESERVATION_STAGING="${STATE}/preservation-staging.json"
INGEST_MANIFEST="${STATE}/ingest-manifest.json"
PRESERVATION_ATLAS="${OUTPUT}/preservation-atlas.json"
PRESERVATION_REPORT="${OUTPUT}/preservation-report.json"
RUN_SEQUENCE_FILE="${STATE}/run-sequence.json"
ensure_dirs() { mkdir -p "${STATE}" "${OUTPUT}"; }
