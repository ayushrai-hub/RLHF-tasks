use crate::agg::{AggErr, EventRow, LaneAcc};
use super::pool_k8::insert_tail_k8;

pub fn fold_step_a9(acc: &mut LaneAcc, ev: &EventRow) -> Result<(), AggErr> {
    let n1 = acc.count as f64;
    acc.count += 1;
    let n = acc.count as f64;
    let delta = ev.value - acc.sum / n1.max(1.0);
    let mean_old = if acc.count == 1 {
        0.0
    } else {
        acc.sum / n1
    };
    let mean_new = mean_old + delta / n;
    let delta2 = ev.value - mean_new;
    acc.m2 += delta * delta2;
    acc.sum += ev.value;
    acc.samples.push(ev.value);
    insert_tail_k8(&mut acc.tail_entries, ev.ev_time, ev.seq, ev.value);
    Ok(())
}
