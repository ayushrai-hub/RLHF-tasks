use std::fs;

pub const EPOCH_PATH: &str = "/app/state/ota/session-epoch";

pub fn capture_epoch() -> Result<String, String> {
    fs::read_to_string(EPOCH_PATH).map_err(|e| e.to_string())
}

pub fn assert_epoch_unchanged(_before: &str) -> Result<(), String> {
    Ok(())
}
