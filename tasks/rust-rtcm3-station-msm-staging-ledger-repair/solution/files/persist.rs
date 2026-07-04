use crate::db;
use crate::ledger;
use crate::seal;
use crate::snapshot;
use crate::staging_manifest;
use crate::types::StagedRow;
use rusqlite::params;
use std::fs::File;
use std::io::{BufRead, BufReader};

fn gap_delta(last: u32, next: u32) -> u32 {
    let diff = if next > last {
        next - last
    } else {
        next.wrapping_sub(last.wrapping_add(1)) + 1
    };
    if diff <= 1 {
        0
    } else {
        diff - 1
    }
}

fn load_staged_rows(staged_path: &str) -> Result<Vec<StagedRow>, String> {
    let reader = BufReader::new(File::open(staged_path).map_err(|e| e.to_string())?);
    let mut rows = Vec::new();
    for line in reader.lines() {
        let line = line.map_err(|e| e.to_string())?;
        if line.trim().is_empty() {
            continue;
        }
        rows.push(serde_json::from_str(&line).map_err(|e| e.to_string())?);
    }
    Ok(rows)
}

pub fn apply_batch(db_path: &str, staged_path: &str, ingest_at: &str) -> Result<(), String> {
    let rows = load_staged_rows(staged_path)?;
    staging_manifest::verify_manifest(staged_path, &rows)?;

    let mut conn = db::open(db_path)?;
    let tx = conn.transaction().map_err(|e| e.to_string())?;

    for row in rows {

        let existing: Option<(u32, i64)> = tx
            .query_row(
                "SELECT last_sequence, gap_count FROM stations WHERE station_key = ?1",
                params![row.station_key],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .ok();

        let new_gap = if let Some((last_seq, gap_count)) = existing {
            gap_count + gap_delta(last_seq, row.sequence) as i64
        } else {
            0i64
        };

        tx.execute(
            "INSERT INTO stations (station_key, station_id, mountpoint, last_sequence, gap_count, observable_sum, last_epoch_ms, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
             ON CONFLICT(station_key) DO UPDATE SET
               last_sequence = excluded.last_sequence,
               gap_count = excluded.gap_count,
               observable_sum = excluded.observable_sum,
               last_epoch_ms = excluded.last_epoch_ms,
               updated_at = excluded.updated_at",
            params![
                row.station_key,
                row.station_id,
                row.mountpoint,
                row.sequence,
                new_gap,
                row.observable_sum,
                row.epoch_ms as i64,
                ingest_at,
            ],
        )
        .map_err(|e| e.to_string())?;

        let event_id = db::new_id("audit");
        tx.execute(
            "INSERT INTO station_audit (event_id, station_key, action, created_at) VALUES (?1, ?2, 'ingested', ?3)",
            params![event_id, row.station_key, ingest_at],
        )
        .map_err(|e| e.to_string())?;
    }

    tx.commit().map_err(|e| e.to_string())?;

    ledger::publish(db_path)?;
    seal::seal(db_path)?;
    snapshot::refresh(db_path, ingest_at)?;
    Ok(())
}

pub fn run(db_path: &str, staged_path: &str, ingest_at: &str) -> Result<(), String> {
    apply_batch(db_path, staged_path, ingest_at)
}
