use crate::agg::fold_a9::fold_step_a9;
use crate::agg::pool_k8::quantile_from_pool;
use crate::agg::BranchTotal;
use crate::agg::{AggErr, BranchAcc, EventRow, LaneAcc, MetricCell, RunReport};
use crate::flow::pair_reduce_r7::parallel_reduce;
use crate::flow::plan_lock_t4::{digest_plan_u1, plan_from_branches};

pub fn oracle_metrics(events: &[EventRow]) -> Result<RunReport, AggErr> {
    let mut by_branch: std::collections::BTreeMap<String, Vec<EventRow>> =
        std::collections::BTreeMap::new();
    for ev in events {
        by_branch
            .entry(ev.branch_id.clone())
            .or_default()
            .push(ev.clone());
    }
    let mut branches = Vec::new();
    for (bid, rows) in by_branch {
        let mut acc = LaneAcc::default();
        let mut max_seq = 0u64;
        let mut part_id = String::new();
        for ev in &rows {
            fold_step_a9(&mut acc, ev)?;
            max_seq = max_seq.max(ev.seq);
            part_id = ev.part_id.clone();
        }
        branches.push(BranchAcc {
            branch_id: bid,
            part_id,
            max_seq,
            acc,
        });
    }
    let plan = plan_from_branches(&branches);
    let (merged, _trace) = parallel_reduce(branches, &plan)?;
    build_report(merged, events, 0, "oracle", 0, &plan)
}

fn build_report(
    merged: BranchAcc,
    events: &[EventRow],
    seed: u64,
    profile: &str,
    frame_gen: u64,
    plan: &[String],
) -> Result<RunReport, AggErr> {
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
    let mut metrics = std::collections::BTreeMap::new();
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
    let mut branch_totals = Vec::new();
    let mut global = 0.0;
    let mut by_b: std::collections::BTreeMap<String, f64> = std::collections::BTreeMap::new();
    for ev in events {
        *by_b.entry(ev.branch_id.clone()).or_default() += ev.value;
    }
    for (bid, total) in by_b {
        global += total;
        branch_totals.push(BranchTotal {
            branch_id: bid,
            total,
        });
    }
    Ok(RunReport {
        seed,
        profile: profile.to_string(),
        metrics,
        global_total: global,
        branch_totals,
        observed_merge_steps: 0,
        frame_gen,
        plan_digest: digest_plan_u1(plan),
    })
}

pub fn oracle_branch_merge(branches: Vec<BranchAcc>) -> Result<BranchAcc, AggErr> {
    let plan = plan_from_branches(&branches);
    let (merged, _trace) = parallel_reduce(branches, &plan)?;
    Ok(merged)
}
