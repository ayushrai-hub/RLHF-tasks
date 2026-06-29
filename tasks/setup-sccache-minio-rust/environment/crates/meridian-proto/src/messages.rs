use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RecordKind {
    Snapshot,
    Delta,
    Heartbeat,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EventRecord {
    pub id: u64,
    pub kind: RecordKind,
    pub payload: String,
}

impl EventRecord {
    pub fn new(id: u64, kind: RecordKind, payload: impl Into<String>) -> Self {
        Self {
            id,
            kind,
            payload: payload.into(),
        }
    }
}
