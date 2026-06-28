#!/bin/bash
set -euo pipefail

cat > /app/environment/src/runtime/reload_dispatch.rs <<'EOF'
use crate::model::ScenarioRow;
use crate::runtime::ack_window::window_ready;

pub fn phase_gate_a(u: &str, rev_hint: u64) -> bool {
    window_ready(u, rev_hint) && rev_hint > 0
}

pub fn dispatch_reload(row: &ScenarioRow) -> (String, bool) {
    let ack = phase_gate_a(&row.primary_unit, row.rev_hint);
    let fresh = ack && row.has_dependency_refresh && row.has_chain_propagation;
    ("success".to_string(), fresh)
}
EOF

cat > /app/environment/src/graph/dep_cache_store.rs <<'EOF'
use crate::graph::chain_state_index::resolve_depth_revision;
use crate::model::ScenarioRow;

pub fn reconcile_b(slice: bool, stamp: bool) -> bool {
    slice && stamp
}

pub fn compute_graph_state(row: &ScenarioRow, dependent_fresh: bool) -> (bool, String) {
    let inactive_ok = reconcile_b(row.inactive_branch_seen, row.inactive_branch_refreshable);
    let depth_revision = resolve_depth_revision(
        dependent_fresh,
        inactive_ok,
        &row.depth_seed,
        row.depth_steps,
    );
    (inactive_ok, depth_revision)
}
EOF

cat > /app/environment/src/graph/chain_state_index.rs <<'EOF'
pub fn resolve_depth_revision(dep: bool, inact: bool, seed: &str, steps: u64) -> String {
    let base = seed.strip_suffix("-stale").unwrap_or(seed);
    let tagged = if base.starts_with("rev-") {
        base.to_string()
    } else {
        format!("rev-{}", base)
    };
    if dep && inact {
        format!("{}-d{}", tagged, steps)
    } else {
        "rev-fallback-d0".to_string()
    }
}
EOF

cat > /app/environment/src/status/status_projection.rs <<'EOF'
use crate::model::StatusView;

pub fn fold_c(seed: bool, echoes: bool) -> StatusView {
    if seed && echoes {
        StatusView { status_color: "green".to_string() }
    } else {
        StatusView { status_color: "amber".to_string() }
    }
}
EOF

/app/environment/scripts/run_probe.sh
