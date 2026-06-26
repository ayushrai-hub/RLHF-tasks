#!/bin/bash
set -euo pipefail
bash /app/environment/migrations/cln_m4.sh
bash /app/environment/scripts/bake_m4.sh
/app/bin/mgr_run --matrix --out /app/output/graph_report.json
