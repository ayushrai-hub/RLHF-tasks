#!/usr/bin/env bash
# run_entry.sh
#
# Pipeline entry point for the reconciliation toolchain. It sources the three
# build modules and drives them in order:
#
#   op_a   (module A, environment/r4/kx/g_extract_k.sh) -> normalized claim rows
#   phase_b(module B, environment/w7/mx/g_plan_m.sh)     -> resolved rows
#   pack_c (module C, environment/r5/px/g_emit_p.sh)     -> the two artifacts
#
# The modules exchange tab-separated rows through a scratch area. This wiring is
# fixed; the reconciliation behaviour lives inside the three module functions.
set -euo pipefail

W7="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_ROOT="$(cd "$W7/.." && pwd)"
OUT_DIR="/app/output"
SCRATCH="$ENV_ROOT/r7/scratch"

mkdir -p "$OUT_DIR" "$SCRATCH"

# shellcheck source=/dev/null
. "$ENV_ROOT/r4/kx/g_extract_k.sh"
# shellcheck source=/dev/null
. "$ENV_ROOT/w7/mx/g_plan_m.sh"
# shellcheck source=/dev/null
. "$ENV_ROOT/r5/px/g_emit_p.sh"

op_a          > "$SCRATCH/claims.tsv"
phase_b       < "$SCRATCH/claims.tsv"  > "$SCRATCH/resolved.tsv"
pack_c        < "$SCRATCH/resolved.tsv"
