#!/usr/bin/env bash
set -euo pipefail
make -C /app/environment
/app/bin/tou_reconcile --config /app/environment/config/run.json --out /app/output/reconciliation_report.json
