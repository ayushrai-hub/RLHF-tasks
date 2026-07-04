use crate::report_metrics;
use chrono::{DateTime, Utc};

fn normalize_as_of(as_of: &str) -> Result<String, String> {
    let parsed = DateTime::parse_from_rfc3339(as_of).map_err(|e| e.to_string())?;
    Ok(parsed.with_timezone(&Utc).format("%Y-%m-%dT%H:%M:%SZ").to_string())
}

pub fn run(db_path: &str, as_of: &str) -> Result<(), String> {
    let _as_of_norm = normalize_as_of(as_of)?;
    let report = report_metrics::from_db(db_path)?;
    println!("{}", serde_json::to_string(&report).map_err(|e| e.to_string())?);
    Ok(())
}
