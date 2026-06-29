#!/usr/bin/env bash
set -euo pipefail
DB=/app/data/pay.db
rm -f "$DB"
echo "removed $DB"
