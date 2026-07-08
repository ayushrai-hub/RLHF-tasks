use std::fs;
use std::path::{Path, PathBuf};

use crate::flow::dur_io::hydrate_frame;
use crate::flow::fence_v2::{active_fence_gen, fence_path};
use crate::flow::lane_materialize_q9::overlay_cache_q9;
use crate::flow::pair_reduce_r7::parallel_reduce;
use crate::flow::plan_lock_t4::plan_from_branches;
use crate::flow::publish::{build_diff, emit_trace, write_diff_summary, write_run_report};
use crate::flow::reuse::apply_cache_pass;
use crate::flow::runner::{
    fold_all_branches, fixture_for_seed, load_cache_state, load_cold_snapshot, load_events,
    report_from_branch, save_cache_state, wal_path, OUT_ROOT, SPAN_MS, VAR_ROOT,
};
use crate::flow::segment_route_s6::routed_tail_rows;
use crate::flow::tail_integrate_r2::integrate_tail_branches_q9;
use crate::flow::wal_j3::wal_seal_peak;
use crate::AggErr;

pub fn run_resume(seed: u64, ckpt: &Path) -> Result<(), AggErr> {
    fs::create_dir_all(VAR_ROOT).ok();
    fs::create_dir_all(OUT_ROOT).ok();
    let events = load_events(&fixture_for_seed(seed))?;
    let split = events.len() / 2;
    let (head, tail) = events.split_at(split);

    let frame = hydrate_frame(ckpt)?;
    let frame_wm = frame.wm;
    let frame_gen = frame.frame_gen;
    let plan = if frame.plan.is_empty() {
        plan_from_branches(&frame.branches)
    } else {
        plan_from_branches(&frame.branches)
    };
    let mut store = load_cache_state()?;
    store.bump_epoch();
    apply_cache_pass(&mut store, head)?;
    let mut branches = frame.branches.clone();
    let (wal_rows, late_rows, live_tail) =
        routed_tail_rows(&wal_path(), tail, frame_wm, frame.processed, frame_gen)?;
    apply_cache_pass(&mut store, &wal_rows)?;
    overlay_cache_q9(&mut branches, &store, &late_rows, SPAN_MS)?;
    integrate_tail_branches_q9(&mut branches, fold_all_branches(&live_tail)?)?;
    let pre_merge = branches.clone();
    let (merged, trace) = parallel_reduce(branches, &plan)?;
    let report = report_from_branch(
        merged,
        &events,
        seed,
        "warm",
        trace.len() as u64,
        frame_gen,
        &plan,
        &pre_merge,
    );

    write_run_report(
        &PathBuf::from(format!("{OUT_ROOT}/run_report.json")),
        &report,
    )?;
    emit_trace(
        &PathBuf::from(format!("{OUT_ROOT}/merge_trace.jsonl")),
        &trace,
    )?;
    let cold = load_cold_snapshot()?;
    let seal_peak = wal_seal_peak(&wal_path());
    let fence_gen = active_fence_gen(&fence_path(), seed);
    // Prefer fence journal when present; falls back to WAL peak.
    let seal_gen = if fence_gen != 0 { fence_gen } else { seal_peak };
    let diff = build_diff(&cold, &report, &trace, seal_gen, store.drain_wm())?;
    write_diff_summary(
        &PathBuf::from(format!("{OUT_ROOT}/resume_diff_summary.json")),
        &diff,
    )?;
    save_cache_state(&store)?;
    Ok(())
}
