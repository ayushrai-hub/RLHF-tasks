use crate::db_fingerprint;
use crate::ledger;
use crate::seal;
use crate::types::SNAPSHOT_PATH;
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Serialize)]
struct SnapshotDoc {
    db_path: String,
    as_of: String,
    db_fingerprint: String,
    station_chain_digest: String,
    mutation_seal_digest: String,
    station_count: i64,
    total_gaps: i64,
    observable_sum_total: f64,
}

#[derive(Deserialize)]
struct StationLedger {
    db_path: String,
    chain_digest: String,
}

fn query_counters(conn: &Connection) -> Result<(i64, i64, f64), String> {
    let station_count: i64 = conn
        .query_row("SELECT COUNT(*) FROM stations", [], |row| row.get(0))
        .map_err(|e| e.to_string())?;
    let total_gaps: i64 = conn
        .query_row(
            "SELECT COALESCE(SUM(gap_count), 0) FROM stations",
            [],
            |row| row.get(0),
        )
        .map_err(|e| e.to_string())?;
    let observable_sum_total: f64 = conn
        .query_row(
            "SELECT COALESCE(SUM(observable_sum), 0.0) FROM stations",
            [],
            |row| row.get(0),
        )
        .map_err(|e| e.to_string())?;
    Ok((station_count, total_gaps, observable_sum_total))
}

pub fn refresh(db_path: &str, as_of: &str) -> Result<(), String> {
    let conn = crate::db::open(db_path)?;
    let ledger_raw = fs::read_to_string(crate::types::LEDGER_PATH)
        .map_err(|_| "station ledger missing".to_string())?;
    let ledger: StationLedger = serde_json::from_str(&ledger_raw).map_err(|e| e.to_string())?;
    if ledger.db_path != db_path {
        return Err("ledger db_path mismatch".to_string());
    }
    let live_digest = ledger::chain_digest(&conn)?;
    if ledger.chain_digest != live_digest {
        return Err("ledger chain_digest stale".to_string());
    }

    let seal = seal::load(db_path)?;
    if seal.ledger_chain_digest != ledger.chain_digest {
        return Err("seal ledger_chain_digest stale".to_string());
    }
    let seal_digest = seal::seal_digest(&seal)?;
    let current_fp = db_fingerprint::file_digest(db_path)?;
    if seal.db_fingerprint != current_fp {
        return Err("seal db_fingerprint stale".to_string());
    }

    let (station_count, total_gaps, observable_sum_total) = query_counters(&conn)?;

    let snapshot = SnapshotDoc {
        db_path: db_path.to_string(),
        as_of: as_of.to_string(),
        db_fingerprint: current_fp,
        station_chain_digest: ledger.chain_digest,
        mutation_seal_digest: seal_digest,
        station_count,
        total_gaps,
        observable_sum_total,
    };

    if let Some(parent) = Path::new(SNAPSHOT_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&snapshot).map_err(|e| e.to_string())?;
    fs::write(SNAPSHOT_PATH, json).map_err(|e| e.to_string())?;
    Ok(())
}
