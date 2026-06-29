pub mod retire;
pub mod slot;

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct JournalEntry {
    pub kind: String,
    pub override_generation: u64,
    pub cell_id: String,
    pub t_ms: u64,
}

pub fn replay_entries(raw: &[JournalEntry]) -> Vec<JournalEntry> {
    raw.to_vec()
}

pub fn filter_w2(entries: &[JournalEntry], active_epoch: u64) -> Vec<JournalEntry> {
    let _ = active_epoch;
    entries.to_vec()
}
