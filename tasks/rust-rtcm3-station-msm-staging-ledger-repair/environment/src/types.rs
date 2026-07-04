use serde::{Deserialize, Serialize};

pub const DEFAULT_LEDGER: &str = "/app/state/rtcmctl-decode-ledger.ndjson";
pub const DEFAULT_STAGED: &str = "/app/state/rtcmctl-staging/staged.ndjson";
pub const LEDGER_PATH: &str = "/app/state/rtcmctl-station-ledger.json";
pub const SEAL_PATH: &str = "/app/state/rtcmctl-mutation-seal.json";
pub const SNAPSHOT_PATH: &str = "/app/state/rtcmctl-snapshot.json";
pub const STAGING_MANIFEST_PATH: &str = "/app/state/rtcmctl-staging-manifest.json";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DecodeRow {
    pub station_id: u16,
    pub mountpoint: String,
    pub sequence: u32,
    pub epoch_ms: u64,
    pub observable_sum: f64,
    pub valid: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StagedRow {
    pub station_key: String,
    pub station_id: u16,
    pub mountpoint: String,
    pub sequence: u32,
    pub epoch_ms: u64,
    pub observable_sum: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct HealthReport {
    pub station_count: i64,
    pub total_gaps: i64,
    pub observable_sum_total: f64,
}
