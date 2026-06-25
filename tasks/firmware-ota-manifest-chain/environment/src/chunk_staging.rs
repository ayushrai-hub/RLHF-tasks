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

pub fn write_staging(_staging: &ChunkMapStaging) -> Result<(), String> {
    Ok(())
}

pub fn load_staging() -> Result<ChunkMapStaging, String> {
    Err("missing verified chunk map staging".to_string())
}
