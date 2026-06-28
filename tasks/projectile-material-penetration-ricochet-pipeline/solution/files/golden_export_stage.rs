use thiserror::Error;

use crate::digest;
use crate::model::{ShotResult, ShotSnapshot};
use crate::staging::{self, StagingError};

#[derive(Debug, Error)]
pub enum ExportStageError {
    #[error("staging error: {0}")]
    Staging(#[from] StagingError),
}

pub fn export_shot_file() -> Result<ShotResult, ExportStageError> {
    let stored = staging::load(std::path::Path::new(staging::SNAPSHOT_PATH))?;
    Ok(build_from_stored(&stored))
}

pub fn publish_shot(snapshot: &ShotSnapshot) -> Result<ShotResult, ExportStageError> {
    staging::persist(snapshot)?;
    export_shot_file()
}

fn build_from_stored(stored: &ShotSnapshot) -> ShotResult {
    ShotResult {
        stack: stored.stack.clone(),
        seed: stored.seed,
        path_ledger_m: round6(stored.path_ledger_m),
        exit_energy_j: round3(stored.exit_energy_j),
        penetrated: stored.penetrated,
        layers: stored.layers.clone(),
        ricochet: stored.ricochet.clone(),
        trace_digest: digest::digest_shot_export(stored.replay_seq, &stored.trace_ids),
    }
}

fn round3(v: f64) -> f64 {
    (v * 1000.0).round() / 1000.0
}

fn round6(v: f64) -> f64 {
    (v * 1_000_000.0).round() / 1_000_000.0
}
