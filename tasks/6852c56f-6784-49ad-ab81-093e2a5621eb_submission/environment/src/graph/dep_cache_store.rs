use crate::graph::chain_state_index::resolve_depth_revision;
use crate::model::ScenarioRow;

pub fn reconcile_b(_slice: bool, _stamp: bool) -> bool {
    false
}

pub fn compute_graph_state(row: &ScenarioRow, dependent_fresh: bool) -> (bool, String) {
    let inactive_ok = reconcile_b(row.inactive_branch_seen, row.inactive_branch_refreshable);
    let depth_revision = resolve_depth_revision(dependent_fresh, inactive_ok, &row.depth_seed, row.depth_steps);
    (inactive_ok, depth_revision)
}
