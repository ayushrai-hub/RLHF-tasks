use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct ScenarioRow {
    pub scenario: String,
    pub primary_unit: String,
    pub rev_hint: u64,
    pub has_dependency_refresh: bool,
    pub has_chain_propagation: bool,
    pub inactive_branch_seen: bool,
    pub inactive_branch_refreshable: bool,
    pub depth_seed: String,
    pub depth_steps: u64,
}

#[derive(Debug, Serialize)]
pub struct ScenarioOut {
    pub scenario: String,
    pub reload_result: String,
    pub dependent_fresh: bool,
    pub inactive_branch_fresh: bool,
    pub depth_revision: String,
    pub status_color: String,
}

#[derive(Debug, Serialize)]
pub struct Summary {
    pub healthy_count: u64,
    pub stale_count: u64,
}

#[derive(Debug, Serialize)]
pub struct Report {
    pub scenarios: Vec<ScenarioOut>,
    pub summary: Summary,
}

#[derive(Debug, Serialize)]
pub struct StatusView {
    pub status_color: String,
}
