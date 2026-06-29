use serde_json::Value;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ValidationError {
    #[error("payload must be a JSON object")]
    NotObject,
    #[error("missing field `{0}`")]
    MissingField(&'static str),
}

pub fn validate_payload(value: &Value) -> Result<(), ValidationError> {
    let object = value.as_object().ok_or(ValidationError::NotObject)?;
    if !object.contains_key("id") {
        return Err(ValidationError::MissingField("id"));
    }
    if !object.contains_key("body") {
        return Err(ValidationError::MissingField("body"));
    }
    Ok(())
}
