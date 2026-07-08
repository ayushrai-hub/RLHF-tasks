#!/usr/bin/env bash
# Tears down the SQLite DB so the next start re-runs schema + seed.
set -euo pipefail
DB_PATH="${DB_PATH:-/app/data/atelier.db}"
rm -f "$DB_PATH" "${DB_PATH}-journal" "${DB_PATH}-wal" "${DB_PATH}-shm"
echo "removed $DB_PATH"
