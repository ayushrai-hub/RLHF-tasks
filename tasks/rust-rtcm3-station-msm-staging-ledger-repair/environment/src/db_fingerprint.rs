use sha2::{Digest, Sha256};
use std::fs;

pub fn file_digest(db_path: &str) -> Result<String, String> {
    let bytes = fs::read(db_path).map_err(|e| e.to_string())?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}
