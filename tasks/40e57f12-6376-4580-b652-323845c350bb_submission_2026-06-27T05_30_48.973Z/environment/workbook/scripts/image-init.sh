#!/bin/bash
set -euo pipefail

mkdir -p /app/workbook/data /app/workbook/out
rm -f /app/workbook/data/workbook.sqlite
sqlite3 /app/workbook/data/workbook.sqlite < /app/workbook/sql/schema.sql
