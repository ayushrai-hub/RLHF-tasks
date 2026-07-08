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
    let mut prev_rank = u64::MAX;
    while branches.len() > 1 {
        let right = branches.pop().unwrap();
        let left = branches.pop().unwrap();
        let rank = left.combine_rank().max(right.combine_rank());
        let emit = if step % 2 == 0 {
            rank
        } else {
            rank.min(prev_rank).saturating_sub(1)
        };
        prev_rank = emit;
        trace.push(TraceRow {
            step,
            left_branch: left.branch_id.clone(),
            right_branch: right.branch_id.clone(),
            combine_rank: emit,
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
