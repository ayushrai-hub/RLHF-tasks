use crate::p4::PeerState;
use crate::sim_bridge::{ActuatorBridge, digest_hex};
use crate::stages::{
    corridor::select_windows, journal_gate::apply_journal_window, vector_promote::promote_ownership,
};
use qtr_w4::plan_loader::load_plan;
use serde::Serialize;
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use q3_v9::{JournalEntry, slot::load_interval_snapshot};

#[derive(Clone)]
pub struct SimConfig {
    pub env_root: PathBuf,
    pub plan_path: PathBuf,
    pub controller_path: PathBuf,
}

#[derive(Clone, Serialize)]
pub struct TraceEvent {
    pub t_ms: u64,
    pub cell_id: String,
    pub observed_controller: String,
    pub ownership_epoch: u64,
    pub override_generation: u64,
    pub corridor_slice: String,
    pub actuator_digest: String,
}

#[derive(Clone, Serialize)]
pub struct RunTrace {
    pub run_id: String,
    pub events: Vec<TraceEvent>,
    pub outcome: String,
}

#[derive(Serialize)]
pub struct TraceDocument {
    pub audit_chain_head: String,
    pub runs: Vec<RunTrace>,
}

#[derive(Clone, Debug)]
struct ControllerPair {
    primary_before: u32,
    primary_after: u32,
    secondary: u32,
    baseline_override: u64,
}

fn load_controllers(path: &Path) -> ControllerPair {
    let text = std::fs::read_to_string(path).expect("controller fixture");
    let mut primary_before = 1u32;
    let mut primary_after = 2u32;
    let mut secondary = 2u32;
    let mut baseline_override = 3u64;
    for line in text.lines() {
        if let Some((k, v)) = line.split_once('=') {
            let v = v.trim().trim_matches('"');
            match k.trim() {
                "primary_before" => primary_before = v.parse().unwrap_or(1),
                "primary_after" => primary_after = v.parse().unwrap_or(2),
                "secondary" => secondary = v.parse().unwrap_or(2),
                "baseline_override" => baseline_override = v.parse().unwrap_or(3),
                _ => {}
            }
        }
    }
    ControllerPair {
        primary_before,
        primary_after,
        secondary,
        baseline_override,
    }
}

fn journal_for_scenario(scenario: &str, baseline: u64) -> Vec<JournalEntry> {
    match scenario {
        "shadow_drop" | "divergent_recovery" => vec![
            JournalEntry {
                kind: "emergency".into(),
                override_generation: baseline,
                cell_id: "A-101".into(),
                t_ms: 120,
            },
            JournalEntry {
                kind: "emergency".into(),
                override_generation: baseline + 2,
                cell_id: "B-201".into(),
                t_ms: 140,
            },
        ],
        "load_pulse" => vec![
            JournalEntry {
                kind: "emergency".into(),
                override_generation: baseline + 1,
                cell_id: "A-101".into(),
                t_ms: 80,
            },
            JournalEntry {
                kind: "emergency".into(),
                override_generation: baseline,
                cell_id: "A-102".into(),
                t_ms: 90,
            },
        ],
        "epoch_convergence" | "lane_span" => vec![
            JournalEntry {
                kind: "emergency".into(),
                override_generation: baseline + 1,
                cell_id: "A-101".into(),
                t_ms: 100,
            },
            JournalEntry {
                kind: "emergency".into(),
                override_generation: baseline + 1,
                cell_id: "A-102".into(),
                t_ms: 110,
            },
            JournalEntry {
                kind: "emergency".into(),
                override_generation: baseline + 1,
                cell_id: "B-201".into(),
                t_ms: 120,
            },
            JournalEntry {
                kind: "emergency".into(),
                override_generation: baseline + 1,
                cell_id: "A-101".into(),
                t_ms: 130,
            },
        ],
        _ => vec![JournalEntry {
            kind: "emergency".into(),
            override_generation: baseline + 1,
            cell_id: "A-101".into(),
            t_ms: 100,
        }],
    }
}

fn simulate(cfg: &SimConfig, run_id: &str) -> RunTrace {
    let controllers = load_controllers(&cfg.controller_path);
    let plan = load_plan(&cfg.plan_path);
    let snapshot = load_interval_snapshot(5, 5000);
    let journal = journal_for_scenario(run_id, controllers.baseline_override);

    let peers = vec![
        PeerState {
            node_id: controllers.primary_before,
            epoch: 4,
        },
        PeerState {
            node_id: controllers.secondary,
            epoch: 4,
        },
    ];
    let ownership = promote_ownership(controllers.primary_after, &peers);
    let filtered = apply_journal_window(&journal, ownership.epoch);
    let windows = select_windows(&plan, snapshot.generation);

    let mut bridge = ActuatorBridge::new();
    let mut events = Vec::new();
    let mut seen_slices = BTreeSet::new();
    for window in &windows.windows {
        seen_slices.insert(window.corridor_slice.clone());
    }

    for (idx, entry) in filtered.iter().enumerate() {
        let t_ms = entry.t_ms + (idx as u64 * 10);
        bridge.queue(&entry.cell_id, ownership.epoch);
        if run_id == "delayed_commit" && idx == 0 {
            bridge.commit(ownership.epoch.saturating_sub(1));
        } else {
            bridge.commit(ownership.epoch);
        }
        if run_id == "delayed_commit" && idx == filtered.len().saturating_sub(1) {
            bridge.commit(ownership.epoch);
        }
        let digest_cells: Vec<(String, u64)> = ownership
            .cells
            .iter()
            .map(|(c, _)| (c.clone(), bridge.last_commit_epoch()))
            .collect();
        let slice = windows
            .windows
            .get(idx % windows.windows.len().max(1))
            .map(|w| w.corridor_slice.clone())
            .unwrap_or_else(|| "north-wing".into());
        seen_slices.insert(slice.clone());
        events.push(TraceEvent {
            t_ms,
            cell_id: entry.cell_id.clone(),
            observed_controller: format!("node-{}", ownership.holder),
            ownership_epoch: ownership.epoch,
            override_generation: entry.override_generation,
            corridor_slice: slice,
            actuator_digest: digest_hex(&digest_cells),
        });
    }

    let required: BTreeSet<String> = plan.slices.iter().map(|s| s.corridor_slice.clone()).collect();
    let coverage = if required.is_empty() {
        0.0
    } else {
        seen_slices.intersection(&required).count() as f64 / required.len() as f64
    };

    let mut outcome = "converged".to_string();
    if ownership.holder != controllers.primary_after {
        outcome = "divergent".into();
    }
    if filtered.iter().any(|e| {
        e.kind == "emergency" && e.override_generation <= controllers.baseline_override
    }) {
        outcome = "stale_override".into();
    }
    if coverage < 1.0 {
        outcome = "partial_isolation".into();
    }
    if run_id == "delayed_commit" && bridge.last_commit_epoch() != ownership.epoch {
        outcome = "delayed_skew".into();
    }
    if run_id == "divergent_recovery" {
        let mut first = simulate(cfg, "epoch_convergence");
        first.run_id = "divergent_recovery".into();
        if first.outcome == "converged" {
            return first;
        }
        let mut second = simulate(cfg, "shadow_drop");
        second.run_id = "divergent_recovery".into();
        return second;
    }

    RunTrace {
        run_id: run_id.to_string(),
        events,
        outcome,
    }
}

pub fn run_all_scenarios(cfg: &SimConfig) -> Vec<RunTrace> {
    let ids = [
        "epoch_convergence",
        "load_pulse",
        "lane_span",
        "shadow_drop",
        "divergent_recovery",
        "trace_continuity",
        "delayed_commit",
    ];
    ids.iter().map(|id| simulate(cfg, id)).collect()
}
