mod parser;

use std::fs;
use std::path::Path;

use parser::parse_log;

use crate::store::Store;

pub struct Options<'a> {
    pub db_path: &'a Path,
    pub log_path: &'a Path,
    pub upload_id: &'a str,
    pub vehicle_id: &'a str,
}

pub fn run(opts: Options<'_>) -> Result<(), String> {
    let store = Store::open(opts.db_path)?;
    if store.upload_committed(opts.upload_id, opts.vehicle_id)? {
        return Ok(());
    }

    let raw = fs::read(opts.log_path).map_err(|e| e.to_string())?;
    let (waypoints, footer) = parse_log(&raw)?;

    if footer.upload_id != opts.upload_id {
        return Err("footer upload_id mismatch".into());
    }
    if footer.expected_count as usize != waypoints.len() {
        return Err("expected_count mismatch".into());
    }

    for wp in &waypoints {
        if wp.upload_id != opts.upload_id {
            return Err("waypoint upload_id mismatch".into());
        }
        store.conn.execute(
            "INSERT OR REPLACE INTO waypoints (vehicle_id, upload_id, seq, lat_e7, lon_e7, alt_mm, frame, flags)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            rusqlite::params![
                opts.vehicle_id,
                opts.upload_id,
                wp.seq,
                wp.lat_e7,
                wp.lon_e7,
                wp.alt_mm,
                wp.frame,
                wp.flags
            ],
        )
        .map_err(|e| e.to_string())?;
    }
    store.conn.execute(
        "INSERT OR IGNORE INTO upload_commits (vehicle_id, upload_id) VALUES (?1, ?2)",
        rusqlite::params![opts.vehicle_id, opts.upload_id],
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
