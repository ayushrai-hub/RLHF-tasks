use serde::{Deserialize, Serialize};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use crate::config::SiteConfig;
use crate::replay::QuarantineRow;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct StreamIdentity {
    pub source: String,
    pub kind: String,
    pub byte_len: u64,
    pub first8: u64,
    pub last8: u64,
    pub byte_sum: u64,
}

impl StreamIdentity {
    pub fn from_bytes(source: &str, kind: &str, data: &[u8]) -> Self {
        fn take8(data: &[u8], from_start: bool) -> u64 {
            let mut buf = [0u8; 8];
            if data.is_empty() {
                return 0;
            }
            if from_start {
                let n = data.len().min(8);
                buf[..n].copy_from_slice(&data[..n]);
            } else {
                let n = data.len().min(8);
                buf[..n].copy_from_slice(&data[data.len() - n..]);
            }
            u64::from_le_bytes(buf)
        }
        let byte_sum = data.iter().fold(0u64, |acc, b| acc.wrapping_add(*b as u64));
        Self {
            source: source.to_string(),
            kind: kind.to_string(),
            byte_len: data.len() as u64,
            first8: take8(data, true),
            last8: take8(data, false),
            byte_sum,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StreamProgress {
    pub identity: StreamIdentity,
    pub consumed_slots: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LiveEvent {
    pub event_id: u64,
    pub timestamp: u64,
    pub raw_hive_id: u16,
    pub canonical_hive_id: u16,
    pub grams: i32,
    pub net_kg: f64,
    pub order: u64,
    pub live: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Frontier {
    pub stream_count: u32,
    pub frame_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PersistedState {
    pub site: String,
    pub events: HashMap<u64, LiveEvent>,
    pub accepted_ids: BTreeSet<u64>,
    pub next_order: u64,
    pub frontier: Frontier,
    pub duplicate_events: u32,
    pub quarantined_frames: u32,
    pub tombstoned_events: u32,
    pub accepted_frames: u32,
    #[serde(default)]
    pub state_epoch: u64,
    #[serde(default)]
    pub streams: HashMap<String, StreamProgress>,
    #[serde(default)]
    pub frame_seq: u64,
}

impl PersistedState {
    pub fn fresh(site: &str) -> Self {
        Self {
            site: site.to_string(),
            events: HashMap::new(),
            accepted_ids: BTreeSet::new(),
            next_order: 1,
            frontier: Frontier {
                stream_count: 0,
                frame_count: 0,
            },
            duplicate_events: 0,
            quarantined_frames: 0,
            tombstoned_events: 0,
            accepted_frames: 0,
            state_epoch: 0,
            streams: HashMap::new(),
            frame_seq: 0,
        }
    }
}

pub struct ReplayState {
    pub cfg: SiteConfig,
    pub data: PersistedState,
    pub quarantine: Vec<QuarantineRow>,
}

impl ReplayState {
    pub fn new(cfg: SiteConfig, site: &str) -> Self {
        Self {
            cfg,
            data: PersistedState::fresh(site),
            quarantine: Vec::new(),
        }
    }

    pub fn from_persisted(cfg: SiteConfig, data: PersistedState) -> Self {
        Self {
            cfg,
            data,
            quarantine: Vec::new(),
        }
    }
}

pub fn state_path(state_dir: &str) -> PathBuf {
    Path::new(state_dir).join("rollup_state.json")
}

pub fn compact_state_path(state_dir: &str) -> PathBuf {
    Path::new(state_dir).join("rollup_state.compact.json")
}

pub fn load_state(path: &Path) -> Result<PersistedState, String> {
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    serde_json::from_str(&text).map_err(|e| e.to_string())
}

pub fn save_state_atomic(path: &Path, state: &PersistedState) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let tmp = path.with_extension("json.tmp");
    let body = serde_json::to_string_pretty(state).map_err(|e| e.to_string())?;
    fs::write(&tmp, body).map_err(|e| e.to_string())?;
    fs::rename(&tmp, path).map_err(|e| e.to_string())
}

pub fn accepted_set(data: &PersistedState) -> HashSet<u64> {
    data.accepted_ids.iter().copied().collect()
}

fn push_state_recovery(rows: &mut Vec<QuarantineRow>) {
    rows.push(QuarantineRow {
        source: String::new(),
        stream_index: 0,
        frame_index: 0,
        reason: "state_recovery".into(),
        event_id: None,
    });
}

pub fn load_resume_state(state_dir: &str) -> Result<(Option<PersistedState>, Vec<QuarantineRow>), String> {
    let dir = Path::new(state_dir);
    let mut recovery: Vec<QuarantineRow> = Vec::new();

    if dir.is_dir() {
        let mut saw_tmp = false;
        for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            let name = entry.file_name().to_string_lossy().into_owned();
            if name.ends_with(".tmp") {
                saw_tmp = true;
            }
        }
        if saw_tmp {
            push_state_recovery(&mut recovery);
        }
    }

    let full = state_path(state_dir);
    let compact = compact_state_path(state_dir);
    let full_exists = full.is_file();
    let compact_exists = compact.is_file();
    let full_parsed = full_exists.then(|| load_state(&full).ok()).flatten();
    let compact_parsed = compact_exists.then(|| load_state(&compact).ok()).flatten();

    if full_exists && full_parsed.is_none() {
        push_state_recovery(&mut recovery);
    }
    if compact_exists && compact_parsed.is_none() && full_parsed.is_some() {
        push_state_recovery(&mut recovery);
    }

    let chosen = match (full_parsed, compact_parsed) {
        (Some(a), Some(b)) => {
            if a.state_epoch >= b.state_epoch {
                a
            } else {
                b
            }
        }
        (Some(a), None) => a,
        (None, Some(b)) => b,
        (None, None) => return Ok((None, recovery)),
    };

    Ok((Some(chosen), recovery))
}
