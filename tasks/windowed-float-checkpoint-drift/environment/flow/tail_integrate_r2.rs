use crate::agg::pair_b2::merge_pair_b2;
use crate::agg::{AggErr, BranchAcc};

pub fn integrate_tail_branches_q9(
    branches: &mut Vec<BranchAcc>,
    tail_branches: Vec<BranchAcc>,
) -> Result<(), AggErr> {
    for b in tail_branches {
        branches.push(b);
    }
    Ok(())
}

pub fn tail_span_hint(branches: &[BranchAcc]) -> u64 {
    branches.iter().map(|b| b.max_seq).max().unwrap_or(0)
}
