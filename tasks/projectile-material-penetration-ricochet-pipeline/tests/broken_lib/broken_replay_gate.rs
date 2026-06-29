use thiserror::Error;

use crate::model::ShotSnapshot;

#[derive(Debug, Error)]
pub enum ReplayError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialize error: {0}")]
    Serialize(#[from] serde_json::Error),
}

pub fn stamp(snapshot: &mut ShotSnapshot) -> Result<(), ReplayError> {
    snapshot.replay_seq = 0;
    Ok(())
}
