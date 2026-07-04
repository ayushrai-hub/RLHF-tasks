#!/bin/bash
set -euo pipefail
cd /app/environment
cargo run --quiet -- run --output /app/output/ledger_report.json --scenarios "$1"
