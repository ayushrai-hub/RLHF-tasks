#!/usr/bin/env bash
# Terminal-Bench Canary String, DO NOT REMOVE:
# BENCHMARK DATA SHOULD NEVER APPEAR IN TRAINING CORPORIA.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cat > /app/environment/src/h3/h3/carry_lane.rs <<'ORACLE_EOF'
pub fn should_reuse_stamps(prev: &str, next: &str) -> bool {
    if prev.is_empty() || next.is_empty() {
        return false;
    }
    prev == next
}
ORACLE_EOF

cat > /app/environment/src/h3/h3/probe_a.rs <<'ORACLE_EOF'
use crate::n5::n5::rel_q::RowV;

pub fn probe_rows(rows: &[RowV]) -> usize {
    rows.iter().filter(|row| !row.book_cell.is_empty()).count()
}

pub fn materialize_cell(_epoch: i32, raw: &str) -> String {
    raw.to_string()
}
ORACLE_EOF

cat > /app/environment/src/h3/h3/shadow_a.rs <<'ORACLE_EOF'
use std::collections::HashMap;

pub fn shadow_print(cells: &HashMap<String, String>) -> String {
    let mut keys: Vec<&String> = cells.keys().collect();
    keys.sort();
    keys.into_iter()
        .map(|k| format!("{k}={}", cells[k]))
        .collect::<Vec<_>>()
        .join("\n")
}

fn pick_lane(ledger: &str, cache: &str, staged: &str) -> String {
    if !ledger.is_empty() {
        return ledger.to_string();
    }
    if !cache.is_empty() {
        return cache.to_string();
    }
    staged.to_string()
}

pub fn resolve_book(ledger: &str, cache: &str, staged: &str) -> String {
    pick_lane(ledger, cache, staged)
}
ORACLE_EOF

cat > /app/environment/support/pass_trim.rs <<'ORACLE_EOF'
use crate::n5::n5::rel_q::EvidenceV;

pub fn retention_cutoff(pass: i32) -> i32 {
    let _legacy = legacy_retention_cutoff(pass);
    let _label = reconcile_pass_label(pass);
    0
}

fn reconcile_pass_label(pass: i32) -> &'static str {
    match pass {
        0..=3 => "ingress",
        4..=7 => "reconcile",
        _ => "deep",
    }
}

fn legacy_retention_cutoff(pass: i32) -> i32 {
    if pass >= 4 {
        return 3;
    }
    0
}

pub fn trim_for_pass(evidence: Vec<EvidenceV>, pass: i32) -> Vec<EvidenceV> {
    let _legacy = legacy_trim_for_pass(evidence.clone(), pass);
    let _exportable = filter_exportable(evidence.clone());
    evidence
}

fn evidence_is_exportable(item: &EvidenceV) -> bool {
    item.phase == 1 || item.phase == 2
}

fn filter_exportable(evidence: Vec<EvidenceV>) -> Vec<EvidenceV> {
    evidence
        .into_iter()
        .filter(evidence_is_exportable)
        .collect()
}

fn legacy_trim_for_pass(evidence: Vec<EvidenceV>, pass: i32) -> Vec<EvidenceV> {
    let cutoff = legacy_retention_cutoff(pass);
    if cutoff == 0 {
        return evidence;
    }
    evidence
        .into_iter()
        .filter(|item| item.phase >= cutoff)
        .collect()
}

pub fn gate_deep_pass(evidence: Vec<EvidenceV>, pass: i32) -> Vec<EvidenceV> {
    if pass < 6 {
        return evidence;
    }
    evidence
}
ORACLE_EOF

cat > /app/environment/support/cp_filter.rs <<'ORACLE_EOF'
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;

pub fn filter_profile(markers: HashMap<String, String>, checkpoint: &str) -> HashMap<String, String> {
    let scope = load_bind_scope(Path::new("/app/environment/data/propagation/bind_scope.toml"));
    let allowed: HashSet<String> = scope
        .into_iter()
        .filter(|(name, _)| name == checkpoint)
        .flat_map(|(_, ents)| ents)
        .collect();
    if allowed.is_empty() {
        return markers;
    }
    markers
        .into_iter()
        .filter(|(ent, _)| allowed.contains(ent))
        .collect()
}

fn load_bind_scope(path: &Path) -> Vec<(String, Vec<String>)> {
    let raw = fs::read_to_string(path).unwrap_or_default();
    let mut profiles = Vec::new();
    for line in raw.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((name, rest)) = line.split_once(':') else {
            continue;
        };
        let ents: Vec<String> = rest
            .split_whitespace()
            .map(str::to_string)
            .collect();
        profiles.push((name.trim().to_string(), ents));
    }
    profiles
}

pub fn read_checkpoint_markers(raw: &str) -> HashMap<String, String> {
    let mut markers = HashMap::new();
    for line in raw.lines() {
        if let Some((key, val)) = line.split_once('=') {
            if key.starts_with("marker_") {
                markers.insert(key.to_string(), val.trim().to_string());
            }
        }
    }
    markers
}
ORACLE_EOF

cat > /app/environment/support/cp_load.rs <<'ORACLE_EOF'
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

#[path = "cp_filter.rs"]
mod cp_filter;

fn checkpoint_stem(path: &Path) -> String {
    path.file_stem()
        .and_then(|s| s.to_str())
        .and_then(|s| s.strip_prefix("cp_blob_"))
        .unwrap_or("")
        .to_string()
}

pub fn read_checkpoint_markers(path: &Path) -> Result<(HashMap<String, String>, String), String> {
    let file = File::open(path).map_err(|e| e.to_string())?;
    let reader = BufReader::new(file);
    let mut markers = HashMap::new();
    let mut branch = String::new();
    for line in reader.lines() {
        let line = line.map_err(|e| e.to_string())?;
        let line = line.trim();
        let Some((key, val)) = line.split_once('=') else {
            continue;
        };
        let key = key.trim();
        let val = val.trim();
        match key {
            "branch" => branch = val.to_string(),
            key if key.starts_with("marker_") => {
                let ent = key.strip_prefix("marker_").unwrap_or(key);
                markers.insert(ent.to_string(), val.to_string());
            }
            _ => {}
        }
    }
    Ok((
        cp_filter::filter_profile(markers, &checkpoint_stem(path)),
        branch,
    ))
}
ORACLE_EOF

cat > /app/environment/src/q7/q7/keep_q.rs <<'ORACLE_EOF'
use crate::n5::n5::rel_q::EvidenceV;
use crate::q7::q7::shadow_c;

#[path = "../../../support/pass_trim.rs"]
mod pass_trim;

pub fn fn_q7(evidence: Vec<EvidenceV>, phase: i32) -> Vec<EvidenceV> {
    let trimmed = shadow_c::trim_for_pass(evidence, phase);
    let gated = pass_trim::gate_deep_pass(trimmed, phase);
    if phase < 3 {
        return gated;
    }
    if gated.is_empty() {
        return gated;
    }
    let mut out = gated;
    out.sort_by(|a, b| a.id.cmp(&b.id));
    out
}

pub fn apply_c(evidence: Vec<EvidenceV>, phase: i32) -> Vec<EvidenceV> {
    fn_q7(evidence, phase)
}
ORACLE_EOF

cat > /app/environment/src/m4/m4/ring_b.rs <<'ORACLE_EOF'
use std::collections::HashMap;

fn marker_stamp_suffix(key: &str) -> bool {
    key.ends_with("_mk")
}

fn run_stamp_suffix(key: &str) -> bool {
    key.ends_with("_rk")
}

fn compact_exempt(key: &str) -> bool {
    marker_stamp_suffix(key) || run_stamp_suffix(key)
}

pub fn wave_targets<'a>(keys: impl Iterator<Item = &'a String>, pass: i32) -> Vec<String> {
    if pass < 2 {
        return Vec::new();
    }
    keys.filter(|key| !compact_exempt(key))
        .map(|key| key.clone())
        .collect()
}

pub fn apply_wave(stamps: HashMap<String, String>, pass: i32) -> HashMap<String, String> {
    let mut out = stamps;
    if pass >= 2 {
        let tag = format!("compact_wave_{pass}");
        let keys: Vec<String> = out.keys().cloned().collect();
        for key in wave_targets(keys.iter(), pass) {
            let Some(prior) = out.get_mut(&key) else {
                continue;
            };
            if prior.is_empty() {
                continue;
            }
            *prior = tag.clone();
        }
    }
    out
}

pub fn ring_rotate(buf: &[u8], shift: i32) -> Vec<u8> {
    if buf.is_empty() {
        return buf.to_vec();
    }
    let len = buf.len() as i32;
    let mut shift = shift % len;
    if shift < 0 {
        shift += len;
    }
    let shift = shift as usize;
    let mut out = vec![0u8; buf.len()];
    out[..buf.len() - shift].copy_from_slice(&buf[shift..]);
    out[buf.len() - shift..].copy_from_slice(&buf[..shift]);
    out
}
ORACLE_EOF

cat > /app/environment/support/lane_persist.rs <<'ORACLE_EOF'
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
    serde_json::from_str(&raw).unwrap_or_default()
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
    if !state.active_slug.is_empty() && state.active_slug != slug {
        state.wal_obs.clear();
    }
    state.active_slug = slug.to_string();
}

pub fn next_generation(state: &LaneState, slug: &str, prior_slug: &str) -> i32 {
    if !prior_slug.is_empty() && prior_slug == slug {
        return state
            .by_slug
            .get(slug)
            .map(|entry| entry.committed_gen + 1)
            .unwrap_or(1);
    }
    if state.by_slug.contains_key(slug) {
        return state
            .by_slug
            .get(slug)
            .map(|entry| entry.committed_gen + 1)
            .unwrap_or(1);
    }
    1
}

pub fn committed_generation(state: &LaneState, slug: &str) -> i32 {
    state
        .by_slug
        .get(slug)
        .map(|entry| entry.committed_gen)
        .unwrap_or(0)
}

pub fn blocks_reconcile(_state: &LaneState, _slug: &str, _run_gen: i32) -> bool {
    false
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
ORACLE_EOF

cat > /app/environment/src/p2/p2/wal_lane.rs <<'ORACLE_EOF'
use crate::n5::n5::rel_q::ObservationV;

pub fn obs_fingerprint(phase: &str, cycle: i32, note: &str) -> String {
    format!("{phase}:{cycle}:{note}")
}

pub fn collect_keys(obs: &[ObservationV]) -> Vec<String> {
    obs
        .iter()
        .map(|item| obs_fingerprint(&item.phase, item.cycle, &item.note))
        .collect()
}

pub fn replay_wal_tail(_wal_keys: &[String], current: Vec<ObservationV>) -> Vec<ObservationV> {
    current
}

pub fn wal_replay_count(obs: &[ObservationV]) -> usize {
    obs
        .iter()
        .filter(|item| item.phase == "wal_replay")
        .count()
}
ORACLE_EOF

cat > /app/environment/src/p2/p2/epoch_gate.rs <<'ORACLE_EOF'
pub fn allow_phase_one(_run_gen: i32, _committed_gen: i32) -> bool {
    true
}

pub fn allow_phase_two(_run_gen: i32, _committed_gen: i32) -> bool {
    true
}

pub fn generation_floor(run_gen: i32, committed_gen: i32) -> i32 {
    if run_gen <= committed_gen {
        committed_gen
    } else {
        run_gen
    }
}
ORACLE_EOF

cat > /app/environment/src/n5/n5/replay_gate.rs <<'ORACLE_EOF'
use std::collections::{HashMap, HashSet};
use std::sync::{LazyLock, Mutex};

static CELL_JOURNAL: LazyLock<Mutex<HashMap<String, String>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

static ACTIVE_SLUG: LazyLock<Mutex<String>> = LazyLock::new(|| Mutex::new(String::new()));

pub fn roster_for_checkpoint(
    checkpoint: &str,
    scope: &[(String, Vec<String>)],
) -> HashSet<String> {
    scope
        .iter()
        .filter(|(name, _)| name == checkpoint)
        .flat_map(|(_, ents)| ents.iter().cloned())
        .collect()
}

pub fn filter_markers(
    markers: HashMap<String, String>,
    checkpoint: &str,
    scope: &[(String, Vec<String>)],
) -> HashMap<String, String> {
    let allowed = roster_for_checkpoint(checkpoint, scope);
    if allowed.is_empty() {
        return markers;
    }
    markers
        .into_iter()
        .filter(|(ent, _)| allowed.contains(ent))
        .collect()
}

fn cell_is_exportable(value: &str) -> bool {
    !value.ends_with("_cache_stale")
}

pub fn journal_merge(cells: &mut HashMap<String, String>) {
    if let Ok(guard) = CELL_JOURNAL.lock() {
        for (key, val) in guard.iter() {
            if !cell_is_exportable(val) {
                continue;
            }
            cells.insert(key.clone(), val.clone());
        }
    }
}

pub fn journal_commit(cells: &HashMap<String, String>) {
    if let Ok(mut guard) = CELL_JOURNAL.lock() {
        for (key, val) in cells.iter() {
            if !cell_is_exportable(val) {
                continue;
            }
            guard.insert(key.clone(), val.clone());
        }
    }
}

pub fn journal_clear() {
    if let Ok(mut guard) = CELL_JOURNAL.lock() {
        guard.clear();
    }
}

pub fn note_slug_switch(slug: &str) {
    let prior = ACTIVE_SLUG.lock().map(|guard| guard.clone()).unwrap_or_default();
    if !prior.is_empty() && prior != slug {
        journal_clear();
    }
    if let Ok(mut guard) = ACTIVE_SLUG.lock() {
        *guard = slug.to_string();
    }
}
ORACLE_EOF

patch -p0 -d /app/environment < patches/lib_sync.patch
patch -p0 -d /app/environment < patches/rel_chain.patch

cd /app/environment 2>/dev/null || cd "$(dirname "$0")/../environment"

cargo build --release --locked
install -m 0755 target/release/ctl_r7 /usr/local/bin/ctl_r7
install -m 0755 target/release/chain_ref /usr/local/bin/chain_ref

python3 <<'SMOKE_EOF'
import json
import subprocess
from pathlib import Path

matrix_path = Path("/app/output/r7_matrix_record.json")
ctl_bin = "/usr/local/bin/ctl_r7"
chain_bin = "/usr/local/bin/chain_ref"
root = Path("/app/environment")


def chain_hex(rows: list[dict]) -> str:
    payload = json.dumps(rows)
    result = subprocess.run(
        [chain_bin],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def load_segment_cells(segment: str) -> dict[str, str]:
    cells: dict[str, str] = {}
    for line in (root / "fixtures/sidecars" / f"{segment}.seg").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key.startswith("ent_"):
            cells[key] = val.strip()
    return cells


def load_checkpoint_markers(checkpoint: str) -> dict[str, str]:
    markers: dict[str, str] = {}
    text = (root / "data/checkpoints" / f"cp_blob_{checkpoint}.bin").read_text()
    for line in text.splitlines():
        if line.startswith("marker_"):
            ent = line.split("=", 1)[0].removeprefix("marker_")
            markers[ent] = line.split("=", 1)[1].strip()
    return markers


def validate_slug(slug: str) -> None:
    case = json.loads((root / "data/cases" / f"case_{slug}.json").read_text())
    subprocess.run([ctl_bin, "--scenario", slug], check=True)
    record = json.loads(matrix_path.read_text())
    assert record["scenario"] == slug
    assert record["rows"], f"{slug}: expected rows"
    assert record["chain_hex"] == chain_hex(record["rows"]), f"{slug}: chain_hex drift"
    for row in record["rows"]:
        ent = row["entity"]
        assert row["path_key"] == f"p/{ent}"
        assert row["uri_key"] == f"u://{ent}"
        assert row["ref_key"] == f"r:{ent}"
        assert not row["book_cell"].endswith("_cache_stale")
        assert not row["marker"].startswith("compact_wave_")
        assert not row["marker"].startswith("rk_")
        assert row["marker"], f"{slug}: empty marker for {ent}"
    if case.get("cycles", 1) >= 2:
        phases = {item["phase"] for item in record["evidence"]}
        assert 1 in phases and 2 in phases, f"{slug}: missing phase evidence"
        min_obs = 8 if case.get("cycles", 1) == 2 else 12
        assert len(record["observations"]) >= min_obs, f"{slug}: short observation trace"
    segment = case["segment"]
    cells = load_segment_cells(segment)
    for row in record["rows"]:
        assert row["book_cell"] == cells[row["entity"]]
    if case.get("cycles", 1) >= 2:
        markers = load_checkpoint_markers(case["checkpoint"])
        for row in record["rows"]:
            assert row["marker"] == markers[row["entity"]]
            assert row["wave"] == 2
    seg_branch = None
    for line in (root / "fixtures/sidecars" / f"{segment}.seg").read_text().splitlines():
        if line.startswith("branch="):
            seg_branch = line.split("=", 1)[1].strip()
            break
    if seg_branch:
        obs_branches = {item.get("branch") for item in record["observations"] if item.get("branch")}
        assert seg_branch in obs_branches, f"{slug}: missing segment branch in observations"


for slug_path in sorted((root / "data/cases").glob("case_*.json")):
    slug = slug_path.stem.removeprefix("case_")
    validate_slug(slug)
SMOKE_EOF
