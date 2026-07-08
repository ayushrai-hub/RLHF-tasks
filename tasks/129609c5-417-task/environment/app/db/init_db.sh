#!/bin/bash
set -euo pipefail
DB="${CALENDAR_DB:-/app/data/calendar.db}"
mkdir -p "$(dirname "$DB")"
sqlite3 "$DB" < /app/db/schema.sql
echo "db initialised at $DB"
