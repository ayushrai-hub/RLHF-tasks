#!/usr/bin/env bash
set -euo pipefail
sqlite3 /app/data/pay.db ".tables"
