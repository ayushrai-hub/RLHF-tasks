use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;

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

pub fn compute_plan_digest(stages: &[String]) -> String {
    let body = stages.join("\n");
    let mut hasher = Sha256::new();
    hasher.update(body.as_bytes());
    hex::encode(hasher.finalize())
}

pub fn write_staging(staging: &ApplyPlanStaging) -> Result<(), String> {
    if let Some(parent) = std::path::Path::new(STAGING_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let body = serde_json::to_string_pretty(staging).map_err(|e| e.to_string())?;
    fs::write(STAGING_PATH, format!("{body}\n")).map_err(|e| e.to_string())
}

pub fn load_staging() -> Result<ApplyPlanStaging, String> {
    let raw = fs::read_to_string(STAGING_PATH)
        .map_err(|_| "missing verified apply plan staging".to_string())?;
    serde_json::from_str(&raw).map_err(|_| "invalid verified apply plan staging".to_string())
}
