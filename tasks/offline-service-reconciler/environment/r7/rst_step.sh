#!/usr/bin/env bash
# rst_step.sh
#
# Destructive re-sync. Running it overwrites the generated artifacts with garbage
# and scrambles the pipeline scratch area. It does not touch the read-only
# surfaces r1/r2/r3. Do not run it to recover; the idempotent recovery command
# is in environment/r6/run_contract.md.
set -euo pipefail

OUT_DIR="/app/output"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRATCH="$HERE/scratch"

mkdir -p "$OUT_DIR" "$SCRATCH"
echo '{ "corrupted": true }' > "$OUT_DIR/inventory_out.json"
echo '{ "corrupted": true }' > "$OUT_DIR/reconcile_report.json"
: > "$SCRATCH/claims.tsv"
echo "garbage" > "$SCRATCH/resolved.tsv"
echo "rst_step: destructive re-sync applied" >&2
