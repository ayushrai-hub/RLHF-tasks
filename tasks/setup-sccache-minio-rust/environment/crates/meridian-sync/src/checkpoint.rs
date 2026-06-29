use meridian_proto::{encode_record, EventRecord, RecordKind};
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Checkpoint {
    pub sequence: u64,
    pub records: Vec<EventRecord>,
}

#[derive(Debug, Error)]
pub enum CheckpointError {
    #[error("checkpoint sequence must increase")]
    StaleSequence,
    #[error(transparent)]
    Codec(#[from] meridian_proto::CodecError),
}

pub struct CheckpointStore {
    latest: Option<Checkpoint>,
}

impl Default for CheckpointStore {
    fn default() -> Self {
        Self { latest: None }
    }
}

impl CheckpointStore {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn commit(&mut self, checkpoint: Checkpoint) -> Result<(), CheckpointError> {
        if let Some(existing) = &self.latest {
            if checkpoint.sequence <= existing.sequence {
                return Err(CheckpointError::StaleSequence);
            }
        }
        for record in &checkpoint.records {
            encode_record(record)?;
        }
        self.latest = Some(checkpoint);
        Ok(())
    }

    pub fn snapshot(&self) -> Option<&Checkpoint> {
        self.latest.as_ref()
    }

    pub fn seed_demo(&mut self) -> Result<(), CheckpointError> {
        let checkpoint = Checkpoint {
            sequence: 1,
            records: vec![
                EventRecord::new(1, RecordKind::Snapshot, "{\"id\":1,\"body\":\"seed\"}"),
                EventRecord::new(2, RecordKind::Delta, "{\"id\":2,\"body\":\"delta\"}"),
            ],
        };
        self.commit(checkpoint)
    }
}
