use crate::types::Envelope;

const STAGING_PATH: &str = "/app/state/ota/verified-envelope.json";

#[derive(serde::Serialize, serde::Deserialize, Clone)]
pub struct VerifiedEnvelopeStaging {
    pub device: String,
    pub envelope: Envelope,
    pub epoch: u32,
    pub verified: bool,
}

pub fn write_staging(_staging: &VerifiedEnvelopeStaging) -> Result<(), String> {
    Ok(())
}

pub fn load_staging() -> Result<VerifiedEnvelopeStaging, String> {
    Err("missing verified envelope staging".to_string())
}
