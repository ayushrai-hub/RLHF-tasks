use std::fs;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const STAGING_PATH: &str = "/app/state/ingest-staging.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StagingLedger {
    pub staging_version: u32,
    pub staging_seq: u32,
    pub conflict_mode: String,
    pub export_mode: String,
    pub candidate_count: u32,
    pub candidate_digest_sha256: String,
}

pub fn candidate_digest(candidates: &[crate::ingest::pipeline::MemoryRecord]) -> String {
    let mut lines = Vec::new();
    for rec in candidates {
        lines.push(format!("{}:{}", rec.memory_id, rec.discovery_seq));
    }
    format!("{:x}", Sha256::digest(lines.join("\n").as_bytes()))
}

pub fn write_staging_ledger(ledger: &StagingLedger) -> Result<(), String> {
    fs::create_dir_all("/app/state").map_err(|e| e.to_string())?;
    fs::write(
        STAGING_PATH,
        format!(
            "{}\n",
            serde_json::to_string_pretty(ledger).map_err(|e| e.to_string())?
        ),
    )
    .map_err(|e| e.to_string())
}

pub fn read_staging_ledger() -> Result<StagingLedger, String> {
    let text = fs::read_to_string(STAGING_PATH).map_err(|_| "missing ingest staging ledger".to_string())?;
    serde_json::from_str(&text).map_err(|e| e.to_string())
}

pub fn digest_staging_bytes(path: &str) -> Result<String, String> {
    let data = fs::read(path).map_err(|e| e.to_string())?;
    Ok(format!("{:x}", Sha256::digest(&data)))
}
