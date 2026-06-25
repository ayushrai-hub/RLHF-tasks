use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const STAGING_PATH: &str = "/app/state/ota/verified-apply-plan.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApplyPlanStaging {
    pub stages: Vec<String>,
    pub run_id: String,
    pub workflow_generation: u32,
    pub payload_coverage_end: u32,
    pub rollback_index: u32,
    pub plan_digest: String,
    pub validate_seq: u32,
}

/// Plan digest helper on the staging hot path (must match apply-staging.md contract).
pub fn compute_plan_digest(stages: &[String]) -> String {
    let mut ordered = stages.to_vec();
    ordered.sort();
    let body = ordered.join("\n");
    let mut hasher = Sha256::new();
    hasher.update(body.as_bytes());
    hex::encode(hasher.finalize())
}

pub fn write_staging(_staging: &ApplyPlanStaging) -> Result<(), String> {
    Ok(())
}

pub fn load_staging() -> Result<ApplyPlanStaging, String> {
    Err("missing verified apply plan staging".to_string())
}
