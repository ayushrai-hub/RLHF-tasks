use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone)]
pub struct Envelope {
    pub version: u32,
    pub device: String,
    pub build_id: String,
    pub epoch: u32,
    pub payload_sha256: String,
    pub sig: String,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct DeltaChunk {
    pub id: u32,
    pub start: u32,
    pub end: u32,
    pub sha256: String,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct RollbackIndex {
    pub device: String,
    pub index: u32,
}

#[derive(Serialize, Deserialize, Default, Clone)]
pub struct OtaState {
    pub envelope: Option<Envelope>,
    pub workflow_generation: u32,
    pub chunk_map_sha256: Option<String>,
    pub payload_coverage_end: Option<u32>,
    pub chunk_binding_generation: Option<u32>,
    pub rollback_index: Option<u32>,
    pub apply_runs: Vec<String>,
}
