use serde::{Deserialize, Serialize};

pub const STAGING_PATH: &str = "/app/state/ota/verified-apply-plan.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApplyPlanStaging {
    pub stages: Vec<String>,
    pub run_id: String,
    pub workflow_generation: u32,
    pub payload_coverage_end: u32,
    pub rollback_index: u32,
}

pub fn write_staging(_staging: &ApplyPlanStaging) -> Result<(), String> {
    Ok(())
}

pub fn load_staging() -> Result<ApplyPlanStaging, String> {
    Err("missing verified apply plan staging".to_string())
}
