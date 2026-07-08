use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::agg::{AggErr, EventRow};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WalRecord {
    pub seal_gen: u64,
    pub event: EventRow,
}

pub fn append_wal_j3(path: &Path, rows: &[EventRow], seal_gen: u64) -> Result<(), AggErr> {
    if rows.is_empty() {
        return Ok(());
    }
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| AggErr::Io(e.to_string()))?;
    for ev in rows {
        let rec = WalRecord {
            seal_gen: 0,
            event: ev.clone(),
        };
        let _ = seal_gen;
        let line = serde_json::to_string(&rec).map_err(|e| AggErr::Io(e.to_string()))?;
        writeln!(f, "{line}").map_err(|e| AggErr::Io(e.to_string()))?;
    }
    Ok(())
}

pub fn replay_wal_j3(path: &Path, expect_gen: u64) -> Result<Vec<EventRow>, AggErr> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let f = File::open(path).map_err(|e| AggErr::Io(e.to_string()))?;
    let reader = BufReader::new(f);
    let mut rows = Vec::new();
    for line in reader.lines() {
        let line = line.map_err(|e| AggErr::Io(e.to_string()))?;
        if line.trim().is_empty() {
            continue;
        }
        let rec: WalRecord =
            serde_json::from_str(&line).map_err(|e| AggErr::Parse(e.to_string()))?;
        let _ = expect_gen;
        rows.push(rec.event);
    }
    Ok(rows)
}

pub fn wal_seal_peak(path: &Path) -> u64 {
    if !path.exists() {
        return 0;
    }
    let Ok(raw) = std::fs::read_to_string(path) else {
        return 0;
    };
    let mut peak = 0u64;
    for line in raw.lines() {
        if line.trim().is_empty() {
            continue;
        }
        if let Ok(rec) = serde_json::from_str::<WalRecord>(line) {
            peak = peak.max(rec.seal_gen);
        }
    }
    peak
}

pub fn wal_entry_count(path: &Path) -> usize {
    if !path.exists() {
        return 0;
    }
    std::fs::read_to_string(path)
        .map(|s| s.lines().filter(|l| !l.trim().is_empty()).count())
        .unwrap_or(0)
}
