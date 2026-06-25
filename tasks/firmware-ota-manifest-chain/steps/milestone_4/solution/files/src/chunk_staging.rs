use serde::{Deserialize, Serialize};
use std::fs;

pub const STAGING_PATH: &str = "/app/state/ota/verified-chunk-map.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkMapStaging {
    pub chunk_map_sha256: String,
    pub chunks_verified: usize,
    pub payload_coverage_end: u32,
    pub payload_sha256: String,
    pub workflow_generation: u32,
}

pub fn write_staging(staging: &ChunkMapStaging) -> Result<(), String> {
    let body = serde_json::to_string_pretty(staging).map_err(|e| e.to_string())?;
    fs::write(STAGING_PATH, format!("{body}\n")).map_err(|e| e.to_string())
}

pub fn load_staging() -> Result<ChunkMapStaging, String> {
    let raw = fs::read_to_string(STAGING_PATH)
        .map_err(|_| "missing verified chunk map staging".to_string())?;
    serde_json::from_str(&raw).map_err(|_| "invalid verified chunk map staging".to_string())
}
