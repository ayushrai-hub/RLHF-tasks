//! Alternate audit digest materialization (unused by publish-ledger).

use rusqlite::Connection;
use serde::Serialize;
use sha2::{Digest, Sha256};

#[derive(Serialize)]
struct AuditRow<'a> {
    event_id: &'a str,
    station_key: &'a str,
    action: &'a str,
    created_at: &'a str,
}

pub fn chain_digest(conn: &Connection) -> Result<String, String> {
    let mut stmt = conn
        .prepare(
            "SELECT event_id, station_key, action, created_at FROM station_audit ORDER BY event_id ASC",
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
