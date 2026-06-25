use serde::{Deserialize, Serialize};
use std::fs;

pub const STAGING_PATH: &str = "/app/state/ota/verified-rollback.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RollbackStaging {
    pub device: String,
    pub index: u32,
    pub current_index: u32,
    pub workflow_generation: u32,
}

pub fn write_staging(staging: &RollbackStaging) -> Result<(), String> {
    if let Some(parent) = std::path::Path::new(STAGING_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let body = serde_json::to_string_pretty(staging).map_err(|e| e.to_string())?;
    fs::write(STAGING_PATH, format!("{body}\n")).map_err(|e| e.to_string())
}

pub fn load_staging() -> Result<RollbackStaging, String> {
    let raw = fs::read_to_string(STAGING_PATH)
        .map_err(|_| "missing verified rollback staging".to_string())?;
    serde_json::from_str(&raw).map_err(|_| "invalid verified rollback staging".to_string())
}
