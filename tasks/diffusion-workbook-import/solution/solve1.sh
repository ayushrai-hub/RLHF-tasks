#!/bin/bash
set -euo pipefail

DIR="$(dirname "$0")"
cp "$DIR/go-resolve.fixed.js" /app/workbook/lib/go-resolve.js
cp "$DIR/001_import.fixed.js" /app/workbook/migrations/001_import.js
/app/workbook/bin/migrate.sh
