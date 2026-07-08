use std::fs;
use std::path::PathBuf;

use crate::ckpt::digest_probe_h5::digest_probe_h5;
use crate::flow::compact_m4::compact_branches_m4;
use crate::flow::dur_io::persist_frame;
use crate::flow::fence_v2::{append_fence_v2, fence_path};
use crate::flow::ingest::frame_from_branches;
use crate::flow::pair_reduce_r7::parallel_reduce;
use crate::flow::plan_lock_t4::plan_from_branches;
use crate::flow::publish::{build_diff, emit_trace, write_diff_summary, write_run_report};
use crate::flow::runner::{
    dur_path, fold_all_branches, fixture_for_seed, load_events, next_frame_gen, report_from_branch,
    save_cold_snapshot, wal_path, OUT_ROOT, VAR_ROOT,
};
use crate::flow::wal_j3::append_wal_j3;
use crate::r#ref::oracle_m7::oracle_metrics;
use crate::AggErr;

pub fn run_cold(seed: u64) -> Result<(), AggErr> {
    fs::create_dir_all(VAR_ROOT).ok();
    fs::create_dir_all(OUT_ROOT).ok();
    if wal_path().exists() {
        fs::remove_file(wal_path()).ok();
    }
    if fence_path().exists() {
        fs::remove_file(fence_path()).ok();
    }
    let events = load_events(&fixture_for_seed(seed))?;
    let split = events.len() / 2;
    let (head, tail) = events.split_at(split);

    let mut head_branches = fold_all_branches(head)?;
    head_branches = compact_branches_m4(head_branches)?;
    let wm = head.iter().map(|e| e.ev_time).max().unwrap_or(0);
    let frame_gen = next_frame_gen(seed);
    let live_branches = fold_all_branches(&events)?;
    let plan = plan_from_branches(&live_branches);
    let mut frame = frame_from_branches(seed, split as u64, wm, frame_gen, head_branches);
    frame.plan = plan.clone();
    let _digest = digest_probe_h5(&frame);
    persist_frame(&dur_path(), &frame)?;
    append_wal_j3(&wal_path(), tail, frame_gen)?;
    append_fence_v2(&fence_path(), seed, frame_gen, "cold_seal")?;

    let pre_merge = live_branches.clone();
    let (merged, trace) = parallel_reduce(live_branches, &plan)?;
    let report = report_from_branch(
        merged,
        &events,
        seed,
        "cold",
        trace.len() as u64,
        frame_gen,
        &plan,
        &pre_merge,
    );
    save_cold_snapshot(&report)?;

    write_run_report(
        &PathBuf::from(format!("{OUT_ROOT}/run_report.json")),
        &report,
    )?;
    emit_trace(
        &PathBuf::from(format!("{OUT_ROOT}/merge_trace.jsonl")),
        &trace,
    )?;
    let oracle = oracle_metrics(&events)?;
    let diff = build_diff(&oracle, &report, &trace, frame_gen, frame_gen)?;
    write_diff_summary(
        &PathBuf::from(format!("{OUT_ROOT}/resume_diff_summary.json")),
        &diff,
    )?;
    Ok(())
}
