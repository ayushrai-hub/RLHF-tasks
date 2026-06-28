#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:/usr/local/bin:${PATH}"
cd /app

SOL=""
for d in "$(dirname "$0")/files" "$(dirname "$0")" /solution/files /solution /oracle/solution; do
  [[ -f "${d}/golden_material.rs" ]] && SOL="$d" && break
done
[[ -n "$SOL" ]] || { echo "golden_material.rs not found" >&2; exit 1; }

cp -f "${SOL}/golden_material.rs" /app/crates/ballcore/src/material.rs
cp -f "${SOL}/golden_integrator.rs" /app/crates/ballcore/src/integrator.rs
cp -f "${SOL}/golden_ricochet.rs" /app/crates/ballcore/src/ricochet.rs
cp -f "${SOL}/golden_batch.rs" /app/crates/ballcore/src/batch.rs
cp -f "${SOL}/golden_staging.rs" /app/crates/ballcore/src/staging.rs
cp -f "${SOL}/golden_export_stage.rs" /app/crates/ballcore/src/export_stage.rs
cp -f "${SOL}/golden_replay_gate.rs" /app/crates/ballcore/src/replay_gate.rs
cp -f "${SOL}/golden_rollup.rs" /app/crates/ballcore/src/rollup.rs
cp -f "${SOL}/golden_digest.rs" /app/crates/ballcore/src/digest.rs

cargo build --offline --release --locked -p ballctl
install -m 0755 /app/target/release/ballctl /usr/local/bin/ballctl
bash /app/scripts/reset-state.sh
echo "ballctl oracle ready"
