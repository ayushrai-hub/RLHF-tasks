use crate::agg::{AggErr, BranchAcc};

pub fn compact_branches_m4(mut branches: Vec<BranchAcc>) -> Result<Vec<BranchAcc>, AggErr> {
    branches.sort_by(|a, b| a.branch_id.cmp(&b.branch_id));
    Ok(branches)
}

pub fn branch_span_hint(branches: &[BranchAcc]) -> u64 {
    branches.iter().map(|b| b.max_seq).max().unwrap_or(0)
}

pub fn compact_preview_len(branches: &[BranchAcc]) -> usize {
    branches.len()
}
