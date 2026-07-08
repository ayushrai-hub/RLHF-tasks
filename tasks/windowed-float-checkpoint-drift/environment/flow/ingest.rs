use crate::agg::fold_a9::fold_step_a9;
use crate::agg::{AggErr, BranchAcc, EventRow, LaneAcc, PartialFrame};
use crate::flow::plan_lock_t4::{digest_plan_u1, plan_from_branches};

pub fn ingest_event(acc: &mut LaneAcc, ev: &EventRow) -> Result<(), AggErr> {
    fold_step_a9(acc, ev)
}

pub fn fold_branch(rows: &[EventRow]) -> Result<BranchAcc, AggErr> {
    let mut acc = LaneAcc::default();
    let mut max_seq = 0u64;
    let mut branch_id = String::new();
    let mut part_id = String::new();
    for ev in rows {
        ingest_event(&mut acc, ev)?;
        max_seq = max_seq.max(ev.seq);
        branch_id = ev.branch_id.clone();
        part_id = ev.part_id.clone();
    }
    Ok(BranchAcc {
        branch_id,
        part_id,
        max_seq,
        acc,
    })
}

pub fn frame_from_branches(
    seed: u64,
    processed: u64,
    wm: u64,
    frame_gen: u64,
    branches: Vec<BranchAcc>,
) -> PartialFrame {
    let plan = plan_from_branches(&branches);
    let _ = digest_plan_u1(&plan);
    PartialFrame {
        seed,
        processed,
        wm,
        frame_gen,
        plan,
        branches,
    }
}
