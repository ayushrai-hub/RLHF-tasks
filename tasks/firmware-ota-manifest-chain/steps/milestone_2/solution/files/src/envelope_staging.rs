use std::fs;

use crate::types::Envelope;

const STAGING_PATH: &str = "/app/state/ota/verified-envelope.json";

#[derive(serde::Serialize, serde::Deserialize, Clone)]
pub struct VerifiedEnvelopeStaging {
    pub device: String,
    pub envelope: Envelope,
    pub epoch: u32,
    pub verified: bool,
}

pub fn write_staging(staging: &VerifiedEnvelopeStaging) -> Result<(), String> {
    if let Some(parent) = std::path::Path::new(STAGING_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let body = serde_json::to_string_pretty(staging).map_err(|e| e.to_string())?;
    fs::write(STAGING_PATH, format!("{body}\n")).map_err(|e| e.to_string())
}

pub fn load_staging() -> Result<VerifiedEnvelopeStaging, String> {
    let raw = fs::read_to_string(STAGING_PATH)
        .map_err(|_| "missing verified envelope staging".to_string())?;
    serde_json::from_str(&raw).map_err(|_| "invalid verified envelope staging".to_string())
}
