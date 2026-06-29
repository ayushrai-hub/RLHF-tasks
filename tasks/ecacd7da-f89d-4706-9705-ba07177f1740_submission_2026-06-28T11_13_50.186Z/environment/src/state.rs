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
