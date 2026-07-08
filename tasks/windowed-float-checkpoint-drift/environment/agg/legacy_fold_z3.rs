use crate::agg::fold_a9::fold_step_a9;
use crate::agg::{AggErr, EventRow, LaneAcc};

pub fn legacy_fold_z3(acc: &mut LaneAcc, ev: &EventRow) -> Result<(), AggErr> {
    let v = ev.value as f32 as f64;
    let slim = EventRow {
        branch_id: ev.branch_id.clone(),
        part_id: ev.part_id.clone(),
        seq: ev.seq,
        ev_time: ev.ev_time,
        value: v,
    };
    fold_step_a9(acc, &slim)
}
