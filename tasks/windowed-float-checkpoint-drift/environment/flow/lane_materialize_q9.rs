use crate::agg::gate_f5::boundary_gate_f5;
use crate::agg::fold_a9::fold_step_a9;
use crate::agg::{AggErr, BranchAcc, EventRow, LaneAcc};
use crate::agg::pair_b2::lane_merge;
use crate::flow::reuse::ReuseStore;

pub fn overlay_cache_q9(
    branches: &mut Vec<BranchAcc>,
    store: &ReuseStore,
    rows: &[EventRow],
    span_ms: u64,
) -> Result<(), AggErr> {
    if rows.is_empty() {
        return Ok(());
    }
    for ev in rows {
        let win = boundary_gate_f5(ev, span_ms);
        let key = store.key_for(&win);
        let Some(cached) = store.get(key).cloned() else {
            continue;
        };
        if let Some(slot) = branches.iter_mut().find(|b| b.branch_id == ev.branch_id) {
            slot.acc = lane_merge(slot.acc.clone(), cached);
            slot.max_seq = slot.max_seq.max(ev.seq);
        } else {
            branches.push(BranchAcc {
                branch_id: ev.branch_id.clone(),
                part_id: ev.part_id.clone(),
                max_seq: ev.seq,
                acc: cached,
            });
        }
    }
    Ok(())
}

pub fn lane_to_branch_q9(lane: LaneAcc, branch_id: &str, part_id: &str, max_seq: u64) -> BranchAcc {
    BranchAcc {
        branch_id: branch_id.to_string(),
        part_id: part_id.to_string(),
        max_seq,
        acc: lane,
    }
}

pub fn replay_lane_into(acc: &mut LaneAcc, lane: &LaneAcc) -> Result<(), AggErr> {
    for v in &lane.samples {
        let ev = EventRow {
            branch_id: String::new(),
            part_id: String::new(),
            seq: 0,
            ev_time: 0,
            value: *v,
        };
        fold_step_a9(acc, &ev)?;
    }
    Ok(())
}

pub fn overlay_preview_count(branches: &[BranchAcc], store: &ReuseStore, rows: &[EventRow], span_ms: u64) -> usize {
    rows.iter()
        .filter(|ev| {
            let win = boundary_gate_f5(ev, span_ms);
            store.get(store.key_for(&win)).is_some()
        })
        .count()
}
