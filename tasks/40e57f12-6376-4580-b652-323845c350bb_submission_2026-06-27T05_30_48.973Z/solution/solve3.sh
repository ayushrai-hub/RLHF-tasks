#!/bin/bash
set -euo pipefail

DIR="$(dirname "$0")"
cp "$DIR/go-resolve.fixed.js" /app/workbook/lib/go-resolve.js
cp "$DIR/001_import.fixed.js" /app/workbook/migrations/001_import.js
cp "$DIR/msd.fixed.js" /app/workbook/lib/msd.js
cp "$DIR/002_summary.fixed.js" /app/workbook/migrations/002_summary.js
cp "$DIR/export-checksum.fixed.js" /app/workbook/lib/export-checksum.js
/app/workbook/bin/migrate.sh
/app/workbook/bin/verify-report.sh
