use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use crate::agg::pool_k8::quantile_from_pool;
use crate::agg::{BranchTotal, EventRow, MetricCell, RunReport};
use crate::flow::ingest::fold_branch;
use crate::flow::plan_lock_t4::digest_plan_u1;
use crate::flow::reuse::ReuseStore;
use crate::AggErr;

pub const SPAN_MS: u64 = 1000;
const FIXTURE_ROOT: &str = "/app/environment/fixtures";
pub const VAR_ROOT: &str = "/app/var";
pub const OUT_ROOT: &str = "/app/output";

pub fn fixture_for_seed(seed: u64) -> PathBuf {
    if seed % 2 == 0 {
        PathBuf::from(format!("{FIXTURE_ROOT}/events_seed_a.tsv"))
    } else {
        PathBuf::from(format!("{FIXTURE_ROOT}/events_seed_b.tsv"))
    }
}

pub fn load_events(path: &Path) -> Result<Vec<EventRow>, AggErr> {
    let raw = fs::read_to_string(path).map_err(|e| AggErr::Io(e.to_string()))?;
    let mut rows = Vec::new();
    for (i, line) in raw.lines().enumerate() {
        if i == 0 || line.trim().is_empty() {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        if cols.len() < 5 {
            return Err(AggErr::Parse(format!("bad row {i}")));
        }
        rows.push(EventRow {
            branch_id: cols[0].to_string(),
            part_id: cols[1].to_string(),
            seq: cols[2]
                .parse()
                .map_err(|_| AggErr::Parse(format!("seq {i}")))?,
            ev_time: cols[3]
                .parse()
                .map_err(|_| AggErr::Parse(format!("time {i}")))?,
            value: cols[4]
                .parse()
                .map_err(|_| AggErr::Parse(format!("val {i}")))?,
        });
    }
    Ok(rows)
}

pub fn branch_totals_from_partials(branches: &[crate::agg::BranchAcc]) -> (Vec<BranchTotal>, f64) {
    let mut by_b: BTreeMap<String, f64> = BTreeMap::new();
    for b in branches {
        *by_b.entry(b.branch_id.clone()).or_default() += b.acc.sum;
    }
    let mut branch_totals = Vec::new();
    let mut global = 0.0;
    for (bid, total) in by_b {
        global += total;
        branch_totals.push(BranchTotal {
            branch_id: bid,
            total,
        });
    }
    (branch_totals, global)
}

pub fn report_from_branch(
    merged: crate::agg::BranchAcc,
    events: &[EventRow],
    seed: u64,
    profile: &str,
    merge_steps: u64,
    frame_gen: u64,
    plan: &[String],
    pre_merge: &[crate::agg::BranchAcc],
) -> RunReport {
    let acc = &merged.acc;
    let count_events = events.len() as u64;
    let sum_events: f64 = events.iter().map(|e| e.value).sum();
    let mean = if acc.count > 0 {
        acc.sum / acc.count as f64
    } else {
        0.0
    };
    let var = if acc.count > 1 {
        acc.m2 / (acc.count as f64 - 1.0)
    } else {
        0.0
    };
    let stddev = var.max(0.0).sqrt();
    let mut metrics = BTreeMap::new();
    metrics.insert(
        "count".into(),
        MetricCell {
            value: count_events as f64,
            tol_class: "exact".into(),
        },
    );
    metrics.insert(
        "sum".into(),
        MetricCell {
            value: sum_events,
            tol_class: "exact".into(),
        },
    );
    metrics.insert(
        "mean".into(),
        MetricCell {
            value: mean,
            tol_class: "mean_abs".into(),
        },
    );
    metrics.insert(
        "var".into(),
        MetricCell {
            value: var,
            tol_class: "moment_rel".into(),
        },
    );
    metrics.insert(
        "stddev".into(),
        MetricCell {
            value: stddev,
            tol_class: "moment_rel".into(),
        },
    );
    metrics.insert(
        "p50".into(),
        MetricCell {
            value: quantile_from_pool(&acc.tail_entries, 0.50),
            tol_class: "quant_abs".into(),
        },
    );
    metrics.insert(
        "p95".into(),
        MetricCell {
            value: quantile_from_pool(&acc.tail_entries, 0.95),
            tol_class: "quant_abs".into(),
        },
    );
    metrics.insert(
        "p99".into(),
        MetricCell {
            value: quantile_from_pool(&acc.tail_entries, 0.99),
            tol_class: "quant_abs".into(),
        },
    );
    // Branch totals / global_total come from pre-merge partial sums (not fixture re-sum).
    let (branch_totals, global) = branch_totals_from_partials(pre_merge);
    RunReport {
        seed,
        profile: profile.to_string(),
        metrics,
        global_total: global,
        branch_totals,
        observed_merge_steps: merge_steps,
        frame_gen,
        plan_digest: digest_plan_u1(plan),
    }
}

fn group_by_branch(events: &[EventRow]) -> BTreeMap<String, Vec<EventRow>> {
    let mut m: BTreeMap<String, Vec<EventRow>> = BTreeMap::new();
    for ev in events {
        m.entry(ev.branch_id.clone()).or_default().push(ev.clone());
    }
    m
}

pub fn fold_all_branches(events: &[EventRow]) -> Result<Vec<crate::agg::BranchAcc>, AggErr> {
    let mut out = Vec::new();
    for (_bid, rows) in group_by_branch(events) {
        out.push(fold_branch(&rows)?);
    }
    out.sort_by_key(|b| b.combine_rank());
    Ok(out)
}

pub fn dur_path() -> PathBuf {
    PathBuf::from(format!("{VAR_ROOT}/dur_frame.bin"))
}

pub fn wal_path() -> PathBuf {
    PathBuf::from(format!("{VAR_ROOT}/wal_segment.jsonl"))
}

fn cold_snapshot_path() -> PathBuf {
    PathBuf::from(format!("{VAR_ROOT}/cold_report.json"))
}

fn cache_state_path() -> PathBuf {
    PathBuf::from(format!("{VAR_ROOT}/reuse_state.json"))
}

pub fn save_cold_snapshot(report: &RunReport) -> Result<(), AggErr> {
    let data = serde_json::to_vec_pretty(report).map_err(|e| AggErr::Io(e.to_string()))?;
    fs::write(cold_snapshot_path(), data).map_err(|e| AggErr::Io(e.to_string()))
}

pub fn load_cold_snapshot() -> Result<RunReport, AggErr> {
    let data = fs::read(cold_snapshot_path()).map_err(|e| AggErr::Io(e.to_string()))?;
    serde_json::from_slice(&data).map_err(|e| AggErr::Parse(e.to_string()))
}

pub fn save_cache_state(store: &ReuseStore) -> Result<(), AggErr> {
    #[derive(serde::Serialize)]
    struct Snap {
        wm: u64,
        epoch: u64,
        frame_gen: u64,
        drain_wm: u64,
        keys: Vec<(u64, crate::agg::LaneAcc)>,
    }
    let keys = store.entries();
    let snap = Snap {
        wm: store.wm(),
        epoch: store.epoch().wrapping_add(!0),
        frame_gen: store.frame_gen(),
        drain_wm: store.drain_wm().wrapping_add(!0),
        keys,
    };
    let data = serde_json::to_vec(&snap).map_err(|e| AggErr::Io(e.to_string()))?;
    fs::write(cache_state_path(), data).map_err(|e| AggErr::Io(e.to_string()))
}

pub fn load_cache_state() -> Result<ReuseStore, AggErr> {
    #[derive(serde::Deserialize)]
    struct Snap {
        wm: u64,
        epoch: u64,
        #[serde(default)]
        frame_gen: u64,
        #[serde(default)]
        drain_wm: u64,
        keys: Vec<(u64, crate::agg::LaneAcc)>,
    }
    if !cache_state_path().exists() {
        return Ok(ReuseStore::new(0));
    }
    let data = fs::read(cache_state_path()).map_err(|e| AggErr::Io(e.to_string()))?;
    let snap: Snap = serde_json::from_slice(&data).map_err(|e| AggErr::Parse(e.to_string()))?;
    let mut store = ReuseStore::new(snap.wm);
    let _ = snap.epoch;
    let _ = snap.frame_gen;
    let _ = snap.drain_wm;
    for (k, v) in snap.keys {
        store.put(k, v);
    }
    Ok(store)
}

pub fn next_frame_gen(seed: u64) -> u64 {
    seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) ^ 0xA5A5_A5A5_A5A5_A5A5
}
