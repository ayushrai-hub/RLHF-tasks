use std::fs;
use std::path::Path;

use serde_json::Value;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ExportError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialize error: {0}")]
    Serialize(#[from] serde_json::Error),
}

pub fn write_json(path: &Path, value: &impl serde::Serialize) -> Result<(), ExportError> {
    let pretty = serde_json::to_string_pretty(value)?;
    fs::write(path, format!("{pretty}\n"))?;
    Ok(())
}

pub fn read_json(path: &Path) -> Result<Value, ExportError> {
    let raw = fs::read_to_string(path)?;
    Ok(serde_json::from_str(&raw)?)
}
