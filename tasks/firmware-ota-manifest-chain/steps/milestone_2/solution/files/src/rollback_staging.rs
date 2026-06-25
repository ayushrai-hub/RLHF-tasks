use serde::{Deserialize, Serialize};

pub const STAGING_PATH: &str = "/app/state/ota/verified-rollback.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RollbackStaging {
    pub device: String,
    pub index: u32,
    pub current_index: u32,
    pub workflow_generation: u32,
}

pub fn write_staging(_staging: &RollbackStaging) -> Result<(), String> {
    Ok(())
}

pub fn load_staging() -> Result<RollbackStaging, String> {
    Err("missing verified rollback staging".to_string())
}
