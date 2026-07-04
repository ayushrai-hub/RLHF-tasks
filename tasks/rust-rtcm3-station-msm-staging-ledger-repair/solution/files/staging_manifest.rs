use crate::types::{StagedRow, STAGING_MANIFEST_PATH};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StagingManifest {
    pub staged_path: String,
    pub row_count: u64,
    pub station_keys: Vec<String>,
    pub keys_digest: String,
}

pub fn keys_digest_sorted(keys: &[String]) -> String {
    let body = keys.join("\n");
    format!("{:x}", Sha256::digest(body.as_bytes()))
}

pub fn write_manifest(staged_path: &str, insertion_order_keys: &[String], row_count: u64) -> Result<(), String> {
    let mut sorted: Vec<String> = insertion_order_keys.to_vec();
    sorted.sort();
    sorted.dedup();

    let manifest = StagingManifest {
        staged_path: staged_path.to_string(),
        row_count,
        station_keys: sorted.clone(),
        keys_digest: keys_digest_sorted(&sorted),
    };

    if let Some(parent) = Path::new(STAGING_MANIFEST_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&manifest).map_err(|e| e.to_string())?;
    fs::write(STAGING_MANIFEST_PATH, json).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn verify_manifest(staged_path: &str, rows: &[StagedRow]) -> Result<(), String> {
    let raw = fs::read_to_string(STAGING_MANIFEST_PATH)
        .map_err(|_| "staging manifest missing; run stage first".to_string())?;
    let manifest: StagingManifest = serde_json::from_str(&raw).map_err(|e| e.to_string())?;

    if manifest.staged_path != staged_path {
        return Err("staging manifest staged_path mismatch".to_string());
    }
    if manifest.row_count != rows.len() as u64 {
        return Err("staging manifest row_count mismatch".to_string());
    }

    let mut keys: Vec<String> = rows.iter().map(|r| r.station_key.clone()).collect();
    keys.sort();
    keys.dedup();

    if manifest.station_keys != keys {
        return Err("staging manifest station_keys mismatch".to_string());
    }

    let expected = keys_digest_sorted(&keys);
    if manifest.keys_digest != expected {
        return Err("staging manifest keys_digest mismatch".to_string());
    }
    Ok(())
}
