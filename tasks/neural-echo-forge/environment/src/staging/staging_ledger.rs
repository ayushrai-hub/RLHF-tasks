use serde::{Deserialize, Serialize};

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

pub fn write_staging_ledger(_ledger: &StagingLedger) -> Result<(), String> {
    Err("neural-echo-forge staging ledger write is not implemented".into())
}

pub fn read_staging_ledger() -> Result<StagingLedger, String> {
    Err("neural-echo-forge staging ledger read is not implemented".into())
}

pub fn digest_staging_bytes(_path: &str) -> Result<String, String> {
    Err("neural-echo-forge staging digest is not implemented".into())
}
