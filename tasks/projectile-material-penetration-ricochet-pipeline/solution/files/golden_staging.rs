use std::fs;
use std::path::Path;

use thiserror::Error;

use crate::model::ShotSnapshot;

pub const SNAPSHOT_PATH: &str = "/app/state/shot-snapshot.json";

#[derive(Debug, Error)]
pub enum StagingError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialize error: {0}")]
    Serialize(#[from] serde_json::Error),
}

pub fn persist(snapshot: &ShotSnapshot) -> Result<(), StagingError> {
    if let Some(parent) = Path::new(SNAPSHOT_PATH).parent() {
        fs::create_dir_all(parent)?;
    }
    let pretty = serde_json::to_string_pretty(snapshot)?;
    fs::write(SNAPSHOT_PATH, format!("{pretty}\n"))?;
    Ok(())
}

pub fn load(path: &Path) -> Result<ShotSnapshot, StagingError> {
    let raw = fs::read_to_string(path)?;
    Ok(serde_json::from_str(&raw)?)
}
