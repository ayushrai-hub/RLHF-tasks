use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use crate::config::{self, SiteConfig};
use crate::replay::QuarantineRow;
use crate::rollup::DailyRow;
use crate::state::{Frontier, LiveEvent, PersistedState};

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
    pub audit_fingerprint: String,
    pub ready: bool,
}

pub fn fnv1a_hex(input: &str) -> String {
    let mut hash = 14695981039346656037u64;
    for byte in input.as_bytes() {
        hash ^= *byte as u64;
        hash = hash.wrapping_mul(1099511628211);
    }
    format!("{:016x}", hash)
}

pub fn compute_audit_fingerprint(
    site: &str,
    daily: &[DailyRow],
    quarantine: &[QuarantineRow],
    events: &std::collections::HashMap<u64, LiveEvent>,
    cfg: &SiteConfig,
) -> String {
    let mut lines = vec![format!("site={site}")];
    for row in daily {
        lines.push(format!(
            "daily|{}|{}|{}|{}|{}|{}",
            row.date,
            row.hive_id,
            format_json_number(row.weight_delta_kg),
            row.samples,
            row.first_event_id,
            row.last_event_id
        ));
    }
    for row in quarantine {
        let event = row
            .event_id
            .map(|id| id.to_string())
            .unwrap_or_else(|| "null".into());
        lines.push(format!(
            "quarantine|{}|{}|{}|{}|{}",
            row.source, row.stream_index, row.frame_index, row.reason, event
        ));
    }
    let mut live_ids: Vec<u64> = events
        .values()
        .filter(|ev| ev.live && events.contains_key(&ev.event_id))
        .map(|ev| ev.event_id)
        .collect();
    live_ids.sort_unstable();
    for event_id in live_ids {
        if let Some(ev) = events.get(&event_id) {
            lines.push(format!(
                "event|{}|{}|{}|{}|{}|{}|{}",
                ev.event_id,
                ev.timestamp,
                ev.raw_hive_id,
                ev.canonical_hive_id,
                ev.grams,
                format_json_number(config::round_field(ev.net_kg, cfg.precision)),
                ev.order
            ));
        }
    }
    lines.push(String::new());
    fnv1a_hex(&lines.join("\n"))
}

fn format_json_number(value: f64) -> String {
    serde_json::Value::Number(
        serde_json::Number::from_f64(value).unwrap_or_else(|| serde_json::Number::from(0)),
    )
    .to_string()
}

pub fn build_summary(
    data: &PersistedState,
    rows: &[DailyRow],
    quarantine: &[QuarantineRow],
    cfg: &SiteConfig,
) -> Summary {
    let mut hives: BTreeSet<u16> = BTreeSet::new();
    let mut dates: BTreeSet<String> = BTreeSet::new();
    for row in rows {
        dates.insert(row.date.clone());
        if row.samples > 0 {
            hives.insert(row.hive_id);
        }
    }
    let total = rows.iter().map(|r| r.weight_delta_kg).sum::<f64>();
    let audit_fingerprint =
        compute_audit_fingerprint(&data.site, rows, quarantine, &data.events, cfg);
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
        audit_fingerprint,
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
