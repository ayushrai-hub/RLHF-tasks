#!/bin/bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:${PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
cd /app/environment

cat > agg/pool_k8.rs <<'RS'
use serde::{Deserialize, Serialize};

pub const TAIL_CAP: usize = 12;

#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq)]
pub struct TailEntry {
    pub ev_time: u64,
    pub seq: u64,
    pub value: f64,
}

pub fn insert_tail_k8(entries: &mut Vec<TailEntry>, ev_time: u64, seq: u64, value: f64) {
    entries.push(TailEntry {
        ev_time,
        seq,
        value,
    });
    entries.sort_by(|a, b| {
        a.ev_time
            .cmp(&b.ev_time)
            .then_with(|| a.seq.cmp(&b.seq))
    });
    if entries.len() > TAIL_CAP {
        let drop_n = entries.len() - TAIL_CAP;
        entries.drain(0..drop_n);
    }
}

pub fn fuse_pool_k8(left: Vec<TailEntry>, right: Vec<TailEntry>) -> Vec<TailEntry> {
    let mut out = left;
    out.extend(right);
    out.sort_by(|a, b| {
        a.ev_time
            .cmp(&b.ev_time)
            .then_with(|| a.seq.cmp(&b.seq))
    });
    if out.len() > TAIL_CAP {
        let start = out.len() - TAIL_CAP;
        out = out[start..].to_vec();
    }
    out
}

pub fn quantile_from_pool(entries: &[TailEntry], q: f64) -> f64 {
    if entries.is_empty() {
        return 0.0;
    }
    let mut vals: Vec<f64> = entries.iter().map(|e| e.value).collect();
    vals.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let idx = ((vals.len() as f64 - 1.0) * q).round() as usize;
    vals[idx.min(vals.len() - 1)]
}

pub fn pool_byte_estimate(entries: &[TailEntry]) -> usize {
    entries.len() * 24
}
RS

cat > ckpt/frame_c4.rs <<'RS'
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::agg::{AggErr, BranchAcc, PartialFrame};

#[derive(Serialize, Deserialize)]
struct WireFrame {
    seed: u64,
    processed: u64,
    wm: u64,
    frame_gen: u64,
    plan: Vec<String>,
    branches: Vec<BranchAcc>,
}

fn to_wire(frame: &PartialFrame) -> WireFrame {
    WireFrame {
        seed: frame.seed,
        processed: frame.processed,
        wm: frame.wm,
        frame_gen: frame.frame_gen,
        plan: frame.plan.clone(),
        branches: frame.branches.clone(),
    }
}

fn from_wire(wf: WireFrame) -> PartialFrame {
    PartialFrame {
        seed: wf.seed,
        processed: wf.processed,
        wm: wf.wm,
        frame_gen: wf.frame_gen,
        plan: wf.plan,
        branches: wf.branches,
    }
}

pub fn write_frame_c4(path: &Path, frame: &PartialFrame) -> Result<(), AggErr> {
    let wire = to_wire(frame);
    let data = serde_json::to_vec(&wire).map_err(|e| AggErr::Io(e.to_string()))?;
    let mut f = File::create(path).map_err(|e| AggErr::Io(e.to_string()))?;
    f.write_all(&data).map_err(|e| AggErr::Io(e.to_string()))
}

pub fn read_frame_c4(path: &Path) -> Result<PartialFrame, AggErr> {
    let mut f = File::open(path).map_err(|e| AggErr::Io(e.to_string()))?;
    let mut buf = Vec::new();
    f.read_to_end(&mut buf).map_err(|e| AggErr::Io(e.to_string()))?;
    let wf: WireFrame = serde_json::from_slice(&buf).map_err(|e| AggErr::Parse(e.to_string()))?;
    Ok(from_wire(wf))
}

pub fn frame_byte_estimate(frame: &PartialFrame) -> usize {
    frame.branches.len() * 64 + frame.processed as usize
}
RS

cat > agg/pair_b2.rs <<'RS'
use super::fold_a9::fold_step_a9;
use super::pool_k8::fuse_pool_k8;
use crate::agg::{AggErr, BranchAcc, EventRow, LaneAcc};

pub fn merge_pair_b2(left: BranchAcc, right: BranchAcc) -> Result<BranchAcc, AggErr> {
    let (first, second) = if left.combine_rank() <= right.combine_rank() {
        (left, right)
    } else {
        (right, left)
    };
    let left_tail = first.acc.tail_entries.clone();
    let right_tail = second.acc.tail_entries;
    let mut acc = first.acc;
    for v in second.acc.samples {
        let ev = EventRow {
            branch_id: second.branch_id.clone(),
            part_id: second.part_id.clone(),
            seq: second.max_seq,
            ev_time: 0,
            value: v,
        };
        fold_step_a9(&mut acc, &ev)?;
    }
    acc.tail_entries = fuse_pool_k8(left_tail, right_tail);
    let max_seq = first.max_seq.max(second.max_seq);
    let part_id = if first.max_seq >= second.max_seq {
        first.part_id
    } else {
        second.part_id
    };
    Ok(BranchAcc {
        branch_id: first.branch_id,
        part_id,
        max_seq,
        acc,
    })
}

pub fn lane_merge(a: LaneAcc, b: LaneAcc) -> LaneAcc {
    let mut out = a;
    for v in b.samples {
        let ev = EventRow {
            branch_id: String::new(),
            part_id: String::new(),
            seq: 0,
            ev_time: 0,
            value: v,
        };
        let _ = fold_step_a9(&mut out, &ev);
    }
    out.tail_entries = fuse_pool_k8(out.tail_entries, b.tail_entries);
    out
}

pub fn absorb_right_first(left: BranchAcc, right: BranchAcc) -> Result<BranchAcc, AggErr> {
    let right_tail = right.acc.tail_entries.clone();
    let left_tail = left.acc.tail_entries;
    let mut acc = right.acc;
    for v in left.acc.samples {
        let ev = EventRow {
            branch_id: left.branch_id.clone(),
            part_id: left.part_id.clone(),
            seq: left.max_seq,
            ev_time: 0,
            value: v,
        };
        fold_step_a9(&mut acc, &ev)?;
    }
    acc.tail_entries = fuse_pool_k8(right_tail, left_tail);
    Ok(BranchAcc {
        branch_id: right.branch_id,
        part_id: right.part_id,
        max_seq: left.max_seq.max(right.max_seq),
        acc,
    })
}

pub fn preview_pair_stats(left: &BranchAcc, right: &BranchAcc) -> (u64, u64) {
    let a = left.acc.count + right.acc.count;
    let b = left.max_seq.max(right.max_seq);
    (a, b)
}

pub fn replay_lane_samples(acc: &LaneAcc) -> Vec<f64> {
    acc.samples.clone()
}
RS

cat > cache/slot_d1.rs <<'RS'
use crate::agg::WindowCtx;

pub fn slot_key_d1(win: &WindowCtx, wm: u64, epoch: u64, frame_gen: u64) -> u64 {
    win.boundary_id
        .wrapping_mul(0x9E37_79B9)
        .wrapping_add(wm)
        .wrapping_add(epoch.wrapping_mul(0x517c_c1b7))
        .wrapping_add(frame_gen.wrapping_mul(0x85eb_ca6b))
}

pub fn slot_preview(win: &WindowCtx) -> u64 {
    win.boundary_id ^ win.span_end
}
RS

cat > flow/plan_lock_t4.rs <<'RS'
use crate::agg::BranchAcc;

pub fn plan_from_branches(branches: &[BranchAcc]) -> Vec<String> {
    let mut ordered: Vec<&BranchAcc> = branches.iter().collect();
    ordered.sort_by(|a, b| {
        a.combine_rank()
            .cmp(&b.combine_rank())
            .then_with(|| a.branch_id.cmp(&b.branch_id))
    });
    ordered.iter().map(|b| b.branch_id.clone()).collect()
}

pub fn digest_plan_u1(plan: &[String]) -> String {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for name in plan {
        for b in name.as_bytes() {
            h ^= u64::from(*b);
            h = h.wrapping_mul(0x1000_0000_01b3);
        }
        h ^= 0xff;
        h = h.wrapping_mul(0x1000_0000_01b3);
    }
    format!("{h:016x}")
}

pub fn order_by_plan(branches: Vec<BranchAcc>, plan: &[String]) -> Vec<BranchAcc> {
    let mut by_id: std::collections::HashMap<String, BranchAcc> = branches
        .into_iter()
        .map(|b| (b.branch_id.clone(), b))
        .collect();
    let mut out = Vec::new();
    for name in plan {
        if let Some(b) = by_id.remove(name) {
            out.push(b);
        }
    }
    let mut rest: Vec<BranchAcc> = by_id.into_values().collect();
    rest.sort_by_key(|b| b.combine_rank());
    out.extend(rest);
    out
}

pub fn plan_preview_len(plan: &[String]) -> usize {
    plan.len()
}
RS

cat > flow/pair_reduce_r7.rs <<'RS'
use crate::agg::pair_b2::merge_pair_b2;
use crate::agg::{AggErr, BranchAcc, TraceRow};
use crate::flow::plan_lock_t4::order_by_plan;

pub fn parallel_reduce(
    branches: Vec<BranchAcc>,
    plan: &[String],
) -> Result<(BranchAcc, Vec<TraceRow>), AggErr> {
    let mut branches = order_by_plan(branches, plan);
    let mut trace = Vec::new();
    let mut step = 1u64;
    let mut prev_rank = 0u64;
    while branches.len() > 1 {
        branches.sort_by_key(|b| b.combine_rank());
        let left = branches.remove(0);
        let right = branches.remove(0);
        let rank = left.combine_rank().max(right.combine_rank()).max(prev_rank);
        prev_rank = rank;
        trace.push(TraceRow {
            step,
            left_branch: left.branch_id.clone(),
            right_branch: right.branch_id.clone(),
            combine_rank: rank,
        });
        step += 1;
        let merged = merge_pair_b2(left, right)?;
        branches.push(merged);
    }
    Ok((branches.remove(0), trace))
}

pub fn reduce_preview(branches: &[BranchAcc]) -> u64 {
    branches.iter().map(|b| b.combine_rank()).max().unwrap_or(0)
}
RS

cat > flow/wal_j3.rs <<'RS'
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
            seal_gen,
            event: ev.clone(),
        };
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
        let Ok(rec) = serde_json::from_str::<WalRecord>(&line) else {
            continue;
        };
        if rec.seal_gen != expect_gen {
            continue;
        }
        rows.push(rec.event);
    }
    rows.sort_by(|a, b| {
        a.ev_time
            .cmp(&b.ev_time)
            .then_with(|| a.seq.cmp(&b.seq))
    });
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
RS

cat > flow/segment_route_s6.rs <<'RS'
use std::path::Path;

use crate::agg::{AggErr, EventRow};
use crate::flow::wal_j3::replay_wal_j3;

pub fn split_wal_tail(
    wal_rows: &[EventRow],
    tail_fixture: &[EventRow],
    frame_wm: u64,
    frame_processed: u64,
) -> (Vec<EventRow>, Vec<EventRow>) {
    let _ = frame_processed;
    let late: Vec<EventRow> = wal_rows
        .iter()
        .filter(|ev| ev.ev_time < frame_wm)
        .cloned()
        .collect();
    let live: Vec<EventRow> = tail_fixture
        .iter()
        .filter(|ev| ev.ev_time >= frame_wm)
        .cloned()
        .collect();
    (late, live)
}

pub fn routed_tail_rows(
    wal_path: &Path,
    tail_fixture: &[EventRow],
    frame_wm: u64,
    frame_processed: u64,
    frame_gen: u64,
) -> Result<(Vec<EventRow>, Vec<EventRow>, Vec<EventRow>), AggErr> {
    let wal_rows = replay_wal_j3(wal_path, frame_gen)?;
    let (late, live) = split_wal_tail(&wal_rows, tail_fixture, frame_wm, frame_processed);
    Ok((wal_rows, late, live))
}

pub fn route_preview_count(wal_rows: &[EventRow], frame_wm: u64) -> usize {
    wal_rows.iter().filter(|ev| ev.ev_time < frame_wm).count()
}
RS

cat > flow/compact_m4.rs <<'RS'
use crate::agg::{AggErr, BranchAcc};

pub fn compact_branches_m4(mut branches: Vec<BranchAcc>) -> Result<Vec<BranchAcc>, AggErr> {
    branches.sort_by_key(|b| b.combine_rank());
    Ok(branches)
}

pub fn branch_span_hint(branches: &[BranchAcc]) -> u64 {
    branches.iter().map(|b| b.max_seq).max().unwrap_or(0)
}

pub fn compact_preview_len(branches: &[BranchAcc]) -> usize {
    branches.len()
}
RS

cat > flow/fence_v2.rs <<'RS'
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::agg::AggErr;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FenceRec {
    pub seed: u64,
    pub frame_gen: u64,
    pub seal_kind: String,
}

pub fn fence_path() -> std::path::PathBuf {
    std::path::PathBuf::from(format!("{}/fence_journal.jsonl", crate::flow::runner::VAR_ROOT))
}

pub fn append_fence_v2(path: &Path, seed: u64, frame_gen: u64, seal_kind: &str) -> Result<(), AggErr> {
    let rec = FenceRec {
        seed,
        frame_gen,
        seal_kind: seal_kind.to_string(),
    };
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| AggErr::Io(e.to_string()))?;
    let line = serde_json::to_string(&rec).map_err(|e| AggErr::Io(e.to_string()))?;
    writeln!(f, "{line}").map_err(|e| AggErr::Io(e.to_string()))
}

pub fn active_fence_gen(path: &Path, seed: u64) -> u64 {
    if !path.exists() {
        return 0;
    }
    let Ok(f) = File::open(path) else {
        return 0;
    };
    let reader = BufReader::new(f);
    let mut last = 0u64;
    for line in reader.lines().flatten() {
        if line.trim().is_empty() {
            continue;
        }
        if let Ok(rec) = serde_json::from_str::<FenceRec>(&line) {
            if rec.seed == seed {
                last = rec.frame_gen;
            }
        }
    }
    last
}

pub fn fence_peak_for_seed(path: &Path, seed: u64) -> u64 {
    active_fence_gen(path, seed)
}
RS

cat > flow/lane_materialize_q9.rs <<'RS'
use crate::agg::gate_f5::boundary_gate_f5;
use crate::agg::fold_a9::fold_step_a9;
use crate::agg::{AggErr, BranchAcc, EventRow, LaneAcc};
use crate::flow::ingest::ingest_event;
use crate::flow::reuse::ReuseStore;

pub fn overlay_cache_q9(
    branches: &mut Vec<BranchAcc>,
    store: &ReuseStore,
    rows: &[EventRow],
    span_ms: u64,
) -> Result<(), AggErr> {
    if rows.is_empty() {
        return Ok(());
    }
    for ev in rows {
        if let Some(slot) = branches.iter_mut().find(|b| b.branch_id == ev.branch_id) {
            ingest_event(&mut slot.acc, ev)?;
            let prev_seq = slot.max_seq;
            slot.max_seq = slot.max_seq.max(ev.seq);
            if ev.seq >= prev_seq {
                slot.part_id = ev.part_id.clone();
            }
        } else {
            let mut acc = LaneAcc::default();
            ingest_event(&mut acc, ev)?;
            branches.push(BranchAcc {
                branch_id: ev.branch_id.clone(),
                part_id: ev.part_id.clone(),
                max_seq: ev.seq,
                acc,
            });
        }
        let _ = store.key_for(&boundary_gate_f5(ev, span_ms));
    }
    Ok(())
}

pub fn lane_to_branch_q9(lane: LaneAcc, branch_id: &str, part_id: &str, max_seq: u64) -> BranchAcc {
    BranchAcc {
        branch_id: branch_id.to_string(),
        part_id: part_id.to_string(),
        max_seq,
        acc: lane,
    }
}

pub fn replay_lane_into(acc: &mut LaneAcc, lane: &LaneAcc) -> Result<(), AggErr> {
    for v in &lane.samples {
        let ev = EventRow {
            branch_id: String::new(),
            part_id: String::new(),
            seq: 0,
            ev_time: 0,
            value: *v,
        };
        fold_step_a9(acc, &ev)?;
    }
    Ok(())
}

pub fn overlay_preview_count(branches: &[BranchAcc], store: &ReuseStore, rows: &[EventRow], span_ms: u64) -> usize {
    rows.iter()
        .filter(|ev| {
            let win = boundary_gate_f5(ev, span_ms);
            store.get(store.key_for(&win)).is_some()
        })
        .count()
}
RS

cat > flow/tail_integrate_r2.rs <<'RS'
use crate::agg::pair_b2::merge_pair_b2;
use crate::agg::{AggErr, BranchAcc};

pub fn integrate_tail_branches_q9(
    branches: &mut Vec<BranchAcc>,
    tail_branches: Vec<BranchAcc>,
) -> Result<(), AggErr> {
    for b in tail_branches {
        if let Some(slot) = branches.iter_mut().find(|x| x.branch_id == b.branch_id) {
            *slot = merge_pair_b2(slot.clone(), b)?;
        } else {
            branches.push(b);
        }
    }
    Ok(())
}

pub fn tail_span_hint(branches: &[BranchAcc]) -> u64 {
    branches.iter().map(|b| b.max_seq).max().unwrap_or(0)
}
RS

python3 <<'PY'
from pathlib import Path

runner = Path("/app/environment/flow/runner.rs")
text = runner.read_text()
old_save = """    let snap = Snap {
        wm: store.wm(),
        epoch: store.epoch().wrapping_add(!0),
        frame_gen: store.frame_gen(),
        drain_wm: store.drain_wm().wrapping_add(!0),
        keys,
    }"""
new_save = """    let snap = Snap {
        wm: store.wm(),
        epoch: store.epoch(),
        frame_gen: store.frame_gen(),
        drain_wm: store.drain_wm(),
        keys,
    }"""
if old_save not in text:
    raise SystemExit("runner.rs save_cache_state patch anchor missing")
text = text.replace(old_save, new_save, 1)

old_load = """    let mut store = ReuseStore::new(snap.wm);
    let _ = snap.epoch;
    let _ = snap.frame_gen;
    let _ = snap.drain_wm;
    for (k, v) in snap.keys {
        store.put(k, v);
    }"""
new_load = """    let mut store = ReuseStore::new(snap.wm);
    store.set_epoch(snap.epoch);
    store.set_frame_gen(snap.frame_gen);
    store.set_drain_wm(snap.drain_wm);
    for (k, v) in snap.keys {
        store.put(k, v);
    }"""
if old_load not in text:
    raise SystemExit("runner.rs load_cache_state patch anchor missing")
text = text.replace(old_load, new_load, 1)
runner.write_text(text)

resume = Path("/app/environment/flow/resume_lane_p8.rs")
text = resume.read_text()
old_plan = """    let plan = if frame.plan.is_empty() {
        plan_from_branches(&frame.branches)
    } else {
        plan_from_branches(&frame.branches)
    };
    let mut store = load_cache_state()?;
    store.bump_epoch();
    apply_cache_pass(&mut store, head)?;"""
new_plan = """    let plan = if frame.plan.is_empty() {
        plan_from_branches(&frame.branches)
    } else {
        frame.plan.clone()
    };
    let mut store = load_cache_state()?;
    store.bump_epoch();
    store.set_frame_gen(frame_gen);
    store.set_drain_wm(frame_gen);
    apply_cache_pass(&mut store, head)?;"""
if old_plan not in text:
    raise SystemExit("resume_lane_p8.rs patch anchor missing")
resume.write_text(text.replace(old_plan, new_plan, 1))
PY

bash /app/environment/scripts/build_stats.sh

/usr/local/bin/stream-stats run --profile cold --seed 42
/usr/local/bin/stream-stats resume --from-checkpoint /app/var/dur_frame.bin --seed 42
