//! Direct SQLite health counter aggregation.

use crate::types::HealthReport;
use rusqlite::Connection;

pub fn from_db(db_path: &str) -> Result<HealthReport, String> {
    let conn = Connection::open(db_path).map_err(|e| e.to_string())?;
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
    Ok(HealthReport {
        station_count,
        total_gaps,
        observable_sum_total,
    })
}
