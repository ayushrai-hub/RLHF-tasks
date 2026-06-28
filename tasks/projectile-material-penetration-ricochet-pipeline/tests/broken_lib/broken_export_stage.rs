use sha2::{Digest, Sha256};
use thiserror::Error;

use crate::model::{ShotResult, ShotSnapshot};
use crate::staging::{self, StagingError};

#[derive(Debug, Error)]
pub enum ExportStageError {
    #[error("staging error: {0}")]
    Staging(#[from] StagingError),
}

pub fn publish_shot(snapshot: &ShotSnapshot) -> Result<ShotResult, ExportStageError> {
    staging::persist(snapshot)?;
    let stored = staging::load(std::path::Path::new(staging::SNAPSHOT_PATH))?;
    Ok(ShotResult {
        stack: stored.stack.clone(),
        seed: stored.seed,
        path_ledger_m: round6(stored.path_ledger_m),
        exit_energy_j: round3(stored.exit_energy_j),
        penetrated: stored.penetrated,
        layers: stored.layers.clone(),
        ricochet: stored.ricochet.clone(),
        trace_digest: digest_sorted_ids(&stored.trace_ids),
    })
}

fn digest_sorted_ids(ids: &[u32]) -> String {
    let mut sorted = ids.to_vec();
    sorted.sort_unstable();
    let body = sorted
        .iter()
        .map(|id| id.to_string())
        .collect::<Vec<_>>()
        .join(",");
    hex_sha256(&body)
}

fn hex_sha256(body: &str) -> String {
    Sha256::digest(body.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

fn round3(v: f64) -> f64 {
    (v * 1000.0).round() / 1000.0
}

fn round6(v: f64) -> f64 {
    (v * 1_000_000.0).round() / 1_000_000.0
}
