use super::fold_a9::fold_step_a9;
use super::pool_k8::fuse_pool_k8;
use crate::agg::{AggErr, BranchAcc, EventRow, LaneAcc};

pub fn merge_pair_b2(left: BranchAcc, right: BranchAcc) -> Result<BranchAcc, AggErr> {
    let left_tail = left.acc.tail_entries.clone();
    let right_tail = right.acc.tail_entries;
    let mut acc = left.acc;
    for v in right.acc.samples {
        let ev = EventRow {
            branch_id: right.branch_id.clone(),
            part_id: right.part_id.clone(),
            seq: right.max_seq,
            ev_time: 0,
            value: v,
        };
        fold_step_a9(&mut acc, &ev)?;
    }
    acc.tail_entries = fuse_pool_k8(left_tail, right_tail);
    Ok(BranchAcc {
        branch_id: left.branch_id,
        part_id: left.part_id,
        max_seq: left.max_seq.max(right.max_seq),
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
    acc.samples.iter().map(|v| *v as f32 as f64).collect()
}
