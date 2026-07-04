use crate::types::LEDGER_PATH;
use rusqlite::Connection;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

#[derive(Serialize)]
struct AuditRow<'a> {
    event_id: &'a str,
    station_key: &'a str,
    action: &'a str,
    created_at: &'a str,
}

#[derive(Serialize)]
struct StationLedger {
    db_path: String,
    event_count: i64,
    chain_digest: String,
}

pub fn chain_digest(conn: &Connection) -> Result<String, String> {
    let mut stmt = conn
        .prepare(
            "SELECT event_id, station_key, action, created_at FROM station_audit ORDER BY created_at ASC, event_id ASC",
        )
        .map_err(|e| e.to_string())?;
    let rows: Vec<(String, String, String, String)> = stmt
        .query_map([], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)))
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    let events: Vec<AuditRow<'_>> = rows
        .iter()
        .map(|(event_id, station_key, action, created_at)| AuditRow {
            event_id,
            station_key,
            action,
            created_at,
        })
        .collect();
    let json = serde_json::to_string(&events).map_err(|e| e.to_string())?;
    Ok(format!("{:x}", Sha256::digest(json.as_bytes())))
}

pub fn publish(db_path: &str) -> Result<(), String> {
    let conn = crate::db::open(db_path)?;
    let event_count: i64 = conn
        .query_row("SELECT COUNT(*) FROM station_audit", [], |row| row.get(0))
        .map_err(|e| e.to_string())?;
    let ledger = StationLedger {
        db_path: db_path.to_string(),
        event_count,
        chain_digest: chain_digest(&conn)?,
    };
    if let Some(parent) = Path::new(LEDGER_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&ledger).map_err(|e| e.to_string())?;
    fs::write(LEDGER_PATH, json).map_err(|e| e.to_string())?;
    Ok(())
}
