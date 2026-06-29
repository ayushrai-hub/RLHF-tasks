use crate::messages::EventRecord;
use meridian_core::validate_payload;
use serde_json::Value;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum CodecError {
    #[error("invalid json")]
    InvalidJson(#[from] serde_json::Error),
    #[error(transparent)]
    Validation(#[from] meridian_core::ValidationError),
}

pub fn encode_record(record: &EventRecord) -> Result<Vec<u8>, CodecError> {
    let value = serde_json::to_value(record)?;
    validate_payload(&value)?;
    Ok(serde_json::to_vec(record)?)
}

pub fn decode_record(bytes: &[u8]) -> Result<EventRecord, CodecError> {
    let record: EventRecord = serde_json::from_slice(bytes)?;
    let value = serde_json::to_value(&record)?;
    validate_payload(&value)?;
    Ok(record)
}
