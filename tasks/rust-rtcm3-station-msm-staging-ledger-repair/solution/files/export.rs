use crate::seal;
use crate::types::{HealthReport, SNAPSHOT_PATH};
use chrono::{DateTime, Utc};
use serde::Deserialize;
use std::fs;

#[derive(Deserialize)]
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

fn normalize_as_of(as_of: &str) -> Result<String, String> {
    let parsed = DateTime::parse_from_rfc3339(as_of).map_err(|e| e.to_string())?;
    Ok(parsed.with_timezone(&Utc).format("%Y-%m-%dT%H:%M:%SZ").to_string())
}

pub fn run(db_path: &str, as_of: &str) -> Result<(), String> {
    let as_of_norm = normalize_as_of(as_of)?;
    let raw = fs::read_to_string(SNAPSHOT_PATH)
        .map_err(|_| "snapshot missing; run refresh-snapshot first".to_string())?;
    let snapshot: SnapshotDoc = serde_json::from_str(&raw).map_err(|e| e.to_string())?;

    if snapshot.db_path != db_path {
        return Err("snapshot db_path mismatch".to_string());
    }
    if snapshot.as_of != as_of_norm {
        return Err("snapshot as_of mismatch".to_string());
    }

    let ledger_raw = fs::read_to_string(crate::types::LEDGER_PATH)
        .map_err(|_| "station ledger missing".to_string())?;
    let ledger: StationLedger = serde_json::from_str(&ledger_raw).map_err(|e| e.to_string())?;
    if snapshot.station_chain_digest != ledger.chain_digest {
        return Err("snapshot station_chain_digest mismatch".to_string());
    }

    let seal = seal::load(db_path)?;
    let seal_digest = seal::seal_digest(&seal)?;
    if snapshot.mutation_seal_digest != seal_digest {
        return Err("snapshot mutation_seal_digest mismatch".to_string());
    }

    let report = HealthReport {
        station_count: snapshot.station_count,
        total_gaps: snapshot.total_gaps,
        observable_sum_total: snapshot.observable_sum_total,
    };
    println!("{}", serde_json::to_string(&report).map_err(|e| e.to_string())?);
    Ok(())
}
