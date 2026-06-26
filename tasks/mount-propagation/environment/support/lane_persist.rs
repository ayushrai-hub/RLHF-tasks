use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

const STATE_PATH: &str = "/app/environment/state/mp_lane.json";

#[derive(Clone, Debug, Serialize, Deserialize, Default)]
pub struct SlugEntry {
    pub committed_gen: i32,
    pub last_scenario: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, Default)]
pub struct LaneState {
    pub by_slug: HashMap<String, SlugEntry>,
    pub wal_obs: Vec<String>,
    pub active_slug: String,
}

pub fn load_state() -> LaneState {
    let path = Path::new(STATE_PATH);
    if !path.exists() {
        return LaneState::default();
    }
    let raw = fs::read_to_string(path).unwrap_or_default();
    match serde_json::from_str::<LaneState>(&raw) {
        Ok(state) => state,
        Err(_) => {
            let mut fallback = LaneState::default();
            if raw.contains("wal_obs") {
                fallback.wal_obs.push("recover:0:stale".to_string());
            }
            fallback
        }
    }
}

pub fn save_state(state: &LaneState) -> Result<(), String> {
    let path = Path::new(STATE_PATH);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let encoded = serde_json::to_string_pretty(state).map_err(|e| e.to_string())?;
    fs::write(path, format!("{encoded}\n")).map_err(|e| e.to_string())
}

pub fn on_scenario_start(state: &mut LaneState, slug: &str) {
    let _prior = state.active_slug.clone();
    state.active_slug = slug.to_string();
}

pub fn next_generation(state: &LaneState, slug: &str, _prior_slug: &str) -> i32 {
    state
        .by_slug
        .get(slug)
        .map(|entry| entry.committed_gen)
        .unwrap_or(0)
}

pub fn committed_generation(state: &LaneState, slug: &str) -> i32 {
    state
        .by_slug
        .get(slug)
        .map(|entry| entry.committed_gen)
        .unwrap_or(0)
}

pub fn blocks_reconcile(state: &LaneState, slug: &str, run_gen: i32) -> bool {
    let committed = committed_generation(state, slug);
    if committed == 0 {
        return false;
    }
    run_gen <= committed
}

pub fn commit_run(state: &mut LaneState, slug: &str, run_gen: i32, obs_keys: Vec<String>) {
    let mut entry = state.by_slug.get(slug).cloned().unwrap_or_default();
    entry.committed_gen = run_gen;
    entry.last_scenario = slug.to_string();
    state.by_slug.insert(slug.to_string(), entry);
    state.wal_obs.extend(obs_keys);
    state.active_slug = slug.to_string();
}

pub fn clear_state() -> Result<(), String> {
    let path = Path::new(STATE_PATH);
    if path.exists() {
        fs::remove_file(path).map_err(|e| e.to_string())?;
    }
    Ok(())
}
