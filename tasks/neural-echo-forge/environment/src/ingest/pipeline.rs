use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryRecord {
    pub memory_id: String,
    pub subject: String,
    pub predicate: String,
    pub object: String,
    pub confidence: f64,
    pub tier: String,
    pub anchor_ms: u64,
    pub source: String,
    pub discovery_seq: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub merged_from: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Snapshot {
    pub snapshot_version: u32,
    pub snapshot_seq: u32,
    pub lines_skipped: u32,
    pub reference_anchor_ms: u64,
    pub sources_loaded: Vec<String>,
    pub active_memories: Vec<MemoryRecord>,
    pub superseded_memories: Vec<MemoryRecord>,
    pub retention_vault: Vec<MemoryRecord>,
    pub ingest_fingerprint: String,
}

pub fn run_ingest() -> Result<u32, String> {
    Err("neural-echo-forge ingest is not implemented".into())
}

pub fn run_export() -> Result<(), String> {
    Err("neural-echo-forge export is not implemented".into())
}
