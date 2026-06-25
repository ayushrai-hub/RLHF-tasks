use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

use crate::types::OtaState;

pub fn read(path: &str) -> Result<Vec<u8>, String> {
    fs::read(path).map_err(|e| format!("read failed: {e}"))
}

pub fn write_json<T: Serialize>(path: &str, value: &T) -> Result<(), String> {
    let body = serde_json::to_string_pretty(value).map_err(|e| e.to_string())?;
    fs::write(path, body).map_err(|e| e.to_string())
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(bytes);
    hex::encode(h.finalize())
}

pub fn load_state(path: &str) -> OtaState {
    match fs::read_to_string(path) {
        Ok(s) => serde_json::from_str(&s).unwrap_or_default(),
        Err(_) => OtaState::default(),
    }
}

pub fn save_state(path: &str, st: &OtaState) -> Result<(), String> {
    if let Some(parent) = Path::new(path).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    write_json(path, st)
}
