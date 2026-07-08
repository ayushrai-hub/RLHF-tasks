use std::fs;

use serde::{Deserialize, Serialize};

use crate::ingest::pipeline::{fingerprint, Snapshot};
use crate::staging::staging_ledger::{self, STAGING_PATH};

pub const RECONCILE_PATH: &str = "/app/state/reconcile-report.json";
const SNAPSHOT_PATH: &str = "/app/state/memory-snapshot.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReconcileReport {
    pub reconcile_version: u32,
    pub snapshot_seq: u32,
    pub staging_seq: u32,
    pub ingest_fingerprint: String,
    pub fingerprint_valid: bool,
    pub staging_digest_sha256: String,
    pub candidate_digest_sha256: String,
    pub conflict_mode: String,
    pub export_mode: String,
}

pub fn run_reconcile() -> Result<(), String> {
    let snapshot_text =
        fs::read_to_string(SNAPSHOT_PATH).map_err(|_| "missing memory snapshot".to_string())?;
    let snapshot: Snapshot =
        serde_json::from_str(&snapshot_text).map_err(|e| e.to_string())?;
    let staging = staging_ledger::read_staging_ledger()?;

    if staging.staging_seq != snapshot.snapshot_seq {
        return Err("staging ledger seq mismatch".into());
    }

    let recomputed = fingerprint(&snapshot);
    let fingerprint_valid = recomputed == snapshot.ingest_fingerprint;
    if !fingerprint_valid {
        return Err("ingest fingerprint invalid".into());
    }

    let staging_digest = staging_ledger::digest_staging_bytes(STAGING_PATH)?;

    let report = ReconcileReport {
        reconcile_version: 1,
        snapshot_seq: snapshot.snapshot_seq,
        staging_seq: staging.staging_seq,
        ingest_fingerprint: snapshot.ingest_fingerprint.clone(),
        fingerprint_valid: true,
        staging_digest_sha256: staging_digest,
        candidate_digest_sha256: staging.candidate_digest_sha256.clone(),
        conflict_mode: staging.conflict_mode.clone(),
        export_mode: staging.export_mode.clone(),
    };

    fs::write(
        RECONCILE_PATH,
        format!(
            "{}\n",
            serde_json::to_string_pretty(&report).map_err(|e| e.to_string())?
        ),
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}

pub fn read_reconcile_report() -> Result<ReconcileReport, String> {
    let text =
        fs::read_to_string(RECONCILE_PATH).map_err(|_| "missing reconcile report".to_string())?;
    serde_json::from_str(&text).map_err(|e| e.to_string())
}
