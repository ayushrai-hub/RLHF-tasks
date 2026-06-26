#!/bin/bash
set -euo pipefail
rm -f /app/output/graph_report.json
rm -rf /app/output/.mgr_stage
mkdir -p /app/output/.mgr_stage
: > /app/output/.mgr_stage/clean_mark
