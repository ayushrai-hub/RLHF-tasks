#!/bin/bash
set -euo pipefail

# Terminal-Bench Canary: event-log-snapshot-compaction-skew solution

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Orient in the tree and skim subsystem documentation.
ls -la /app/environment
sed -n '1,15p' /app/environment/docs/architecture.md
sed -n '1,12p' /app/environment/docs/layout_notes.md
sed -n '1,20p' /app/environment/docs/report_schema.md
sed -n '1,10p' /app/environment/docs/state_notes.md
head -25 /app/environment/config/bundles.toml

# Reproduce branch divergence on a bundled scenario before editing.
bash /app/environment/tools/divergence_probe.sh copper_wire_fan || true
bash /app/environment/tools/divergence_probe.sh quartz_ledger_skew || true

# Locate forced-branch and compaction code in the flat module layout.
grep -rn 'crash_resume\|compaction_replay\|fold_x\|raise_w\|seal_v' \
  /app/environment/flow /app/environment/journal /app/environment/codec /app/environment/core

# Read the checkpoint codec and journal fold paths implicated by the probe.
sed -n '1,45p' /app/environment/codec/frame.rs
sed -n '1,55p' /app/environment/journal/merge.rs
sed -n '1,55p' /app/environment/journal/apply.rs
sed -n '1,80p' /app/environment/flow/matrix.rs
sed -n '1,60p' /app/environment/core/ledger.rs

# Fixes span checkpoint framing, mid-batch resume, journal fold/apply, and branch drivers.
cp "$ROOT_DIR/files/codec/frame.rs" /app/environment/codec/frame.rs
cp "$ROOT_DIR/files/core/ledger.rs" /app/environment/core/ledger.rs
cp "$ROOT_DIR/files/journal/merge.rs" /app/environment/journal/merge.rs
cp "$ROOT_DIR/files/journal/apply.rs" /app/environment/journal/apply.rs
cp "$ROOT_DIR/files/flow/matrix.rs" /app/environment/flow/matrix.rs

# Confirm probes and matrix runner succeed after the source repair.
bash /app/environment/tools/divergence_probe.sh copper_wire_fan
bash /app/environment/tools/staging_roundtrip.sh copper_wire_fan
bash /app/environment/tools/run_matrix.sh
