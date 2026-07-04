use crate::db_fingerprint;
use crate::ledger;
use crate::types::{LEDGER_PATH, SEAL_PATH};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

#[derive(Serialize, Deserialize, Clone)]
pub struct MutationSeal {
    pub db_path: String,
    pub ledger_chain_digest: String,
    pub event_count: i64,
    pub db_fingerprint: String,
    pub tail_created_at: String,
}

#[derive(Deserialize)]
struct StationLedger {
    db_path: String,
    event_count: i64,
    chain_digest: String,
}

fn tail_created_at(conn: &Connection) -> Result<String, String> {
    let mut stmt = conn
        .prepare(
            "SELECT created_at FROM station_audit ORDER BY created_at ASC, event_id ASC",
        )
        .map_err(|e| e.to_string())?;
    let rows: Vec<String> = stmt
        .query_map([], |row| row.get(0))
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;
    Ok(rows.last().cloned().unwrap_or_default())
}

pub fn seal_digest(seal: &MutationSeal) -> Result<String, String> {
    let json = format!(
        r#"{{"db_fingerprint":"{}","db_path":"{}","event_count":{},"ledger_chain_digest":"{}","tail_created_at":"{}"}}"#,
        seal.db_fingerprint,
        seal.db_path,
        seal.event_count,
        seal.ledger_chain_digest,
        seal.tail_created_at,
    );
    Ok(format!("{:x}", Sha256::digest(json.as_bytes())))
}

pub fn seal(db_path: &str) -> Result<(), String> {
    let raw = fs::read_to_string(LEDGER_PATH)
        .map_err(|_| "station ledger missing; run publish-ledger first".to_string())?;
    let ledger: StationLedger = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    if ledger.db_path != db_path {
        return Err("station ledger db_path mismatch".to_string());
    }

    let conn = crate::db::open(db_path)?;
    let live_digest = ledger::chain_digest(&conn)?;
    if ledger.chain_digest != live_digest {
        return Err("station ledger chain_digest stale".to_string());
    }

    let seal = MutationSeal {
        db_path: db_path.to_string(),
        ledger_chain_digest: ledger.chain_digest,
        event_count: ledger.event_count,
        db_fingerprint: db_fingerprint::file_digest(db_path)?,
        tail_created_at: tail_created_at(&conn)?,
    };

    if let Some(parent) = Path::new(SEAL_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&seal).map_err(|e| e.to_string())?;
    fs::write(SEAL_PATH, json).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn load(db_path: &str) -> Result<MutationSeal, String> {
    let raw = fs::read_to_string(SEAL_PATH)
        .map_err(|_| "mutation seal missing; run seal-mutations first".to_string())?;
    let seal: MutationSeal = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    if seal.db_path != db_path {
        return Err("mutation seal db_path mismatch".to_string());
    }
    Ok(seal)
}
