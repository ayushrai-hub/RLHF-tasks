use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use crate::config::{self, SiteConfig};
use crate::replay::QuarantineRow;
use crate::rollup::DailyRow;
use crate::state::{Frontier, PersistedState};

#[derive(Debug, serde::Serialize, PartialEq)]
pub struct Summary {
    pub site: String,
    pub total_delta_kg: f64,
    pub days_processed: u32,
    pub hives_seen: Vec<u16>,
    pub accepted_frames: u32,
    pub duplicate_events: u32,
    pub quarantined_frames: u32,
    pub tombstoned_events: u32,
    pub state_frontier: Frontier,
    pub ready: bool,
}

pub fn build_summary(data: &PersistedState, rows: &[DailyRow], cfg: &SiteConfig) -> Summary {
    let mut hives: BTreeSet<u16> = BTreeSet::new();
    let mut dates: BTreeSet<String> = BTreeSet::new();
    for row in rows {
        dates.insert(row.date.clone());
        if row.samples > 0 {
            hives.insert(row.hive_id);
        }
    }
    let total = rows.iter().map(|r| r.weight_delta_kg).sum::<f64>();
    Summary {
        site: data.site.clone(),
        total_delta_kg: config::round_field(total, cfg.precision),
        days_processed: dates.len() as u32,
        hives_seen: hives.into_iter().collect(),
        accepted_frames: data.accepted_frames,
        duplicate_events: data.duplicate_events,
        quarantined_frames: data.quarantined_frames,
        tombstoned_events: data.tombstoned_events,
        state_frontier: data.frontier.clone(),
        ready: !rows.is_empty(),
    }
}

fn ensure_parent(path: &str) -> Result<(), String> {
    if let Some(parent) = Path::new(path).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    Ok(())
}

pub fn write_daily(path: &str, rows: &[DailyRow]) -> Result<(), String> {
    ensure_parent(path)?;
    let mut out = String::new();
    for row in rows {
        out.push_str(&serde_json::to_string(row).map_err(|e| e.to_string())?);
        out.push('\n');
    }
    fs::write(path, out).map_err(|e| e.to_string())
}

pub fn write_summary(path: &str, summary: &Summary) -> Result<(), String> {
    ensure_parent(path)?;
    let body = serde_json::to_string_pretty(summary).map_err(|e| e.to_string())?;
    fs::write(path, body).map_err(|e| e.to_string())
}

pub fn write_quarantine(path: &str, rows: &[QuarantineRow]) -> Result<(), String> {
    ensure_parent(path)?;
    let mut out = String::new();
    for row in rows {
        out.push_str(&serde_json::to_string(row).map_err(|e| e.to_string())?);
        out.push('\n');
    }
    fs::write(path, out).map_err(|e| e.to_string())
}
