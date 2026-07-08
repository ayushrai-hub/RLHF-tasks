use crate::agg::fold_a9::fold_step_a9;
use crate::agg::{AggErr, BranchAcc, EventRow};
use crate::agg::pool_k8::{fuse_pool_k8, TailEntry, TAIL_CAP};

fn fuse_rank(left: Vec<TailEntry>, right: Vec<TailEntry>) -> Vec<TailEntry> {
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

fn merge_pair_rank(left: BranchAcc, right: BranchAcc) -> Result<BranchAcc, AggErr> {
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
    acc.tail_entries = fuse_rank(left_tail, right_tail);
    Ok(BranchAcc {
        branch_id: first.branch_id,
        part_id: first.part_id,
        max_seq: first.max_seq.max(second.max_seq),
        acc,
    })
}

pub fn replay_pair_e3(mut branches: Vec<BranchAcc>) -> Result<BranchAcc, AggErr> {
    branches.sort_by_key(|b| b.combine_rank());
    let mut cur = branches.remove(0);
    for nxt in branches {
        cur = merge_pair_rank(cur, nxt)?;
    }
    Ok(cur)
}

pub fn replay_from_events(events: &[EventRow]) -> Result<BranchAcc, AggErr> {
    let mut acc = crate::agg::LaneAcc::default();
    for ev in events {
        fold_step_a9(&mut acc, ev)?;
    }
    Ok(BranchAcc {
        branch_id: "replay".into(),
        part_id: "r0".into(),
        max_seq: events.last().map(|e| e.seq).unwrap_or(0),
        acc,
    })
}

pub fn replay_lane_fuse(left: Vec<TailEntry>, right: Vec<TailEntry>) -> Vec<TailEntry> {
    fuse_rank(left, right)
}

pub fn replay_lane_fuse_broken(left: Vec<TailEntry>, right: Vec<TailEntry>) -> Vec<TailEntry> {
    fuse_pool_k8(left, right)
}
