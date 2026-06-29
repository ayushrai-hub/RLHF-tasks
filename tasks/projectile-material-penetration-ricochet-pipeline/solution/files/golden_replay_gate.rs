use std::collections::HashMap;
use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::model::ShotSnapshot;

pub const HISTORY_PATH: &str = "/app/state/replay-history.json";

#[derive(Debug, Default, Serialize, Deserialize)]
struct HistoryBody {
    counts: HashMap<String, u64>,
}

#[derive(Debug, Error)]
pub enum ReplayError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialize error: {0}")]
    Serialize(#[from] serde_json::Error),
}

fn load_history() -> Result<HistoryBody, ReplayError> {
    let path = Path::new(HISTORY_PATH);
    if !path.exists() {
        return Ok(HistoryBody::default());
    }
    let raw = fs::read_to_string(path)?;
    Ok(serde_json::from_str(&raw)?)
}

fn save_history(body: &HistoryBody) -> Result<(), ReplayError> {
    if let Some(parent) = Path::new(HISTORY_PATH).parent() {
        fs::create_dir_all(parent)?;
    }
    let pretty = serde_json::to_string_pretty(body)?;
    fs::write(HISTORY_PATH, format!("{pretty}\n"))?;
    Ok(())
}

pub fn stamp(snapshot: &mut ShotSnapshot) -> Result<(), ReplayError> {
    let key = format!("{}:{}", snapshot.stack, snapshot.seed);
    let mut body = load_history()?;
    let seq = body.counts.get(&key).copied().unwrap_or(0);
    snapshot.replay_seq = seq;
    body.counts.insert(key, seq + 1);
    save_history(&body)?;
    Ok(())
}
