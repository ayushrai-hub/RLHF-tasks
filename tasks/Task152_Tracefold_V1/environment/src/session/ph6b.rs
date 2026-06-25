use crate::pool::churn_m;
use crate::pool::slot::Slot;

use super::{Driver, vtxt};

pub fn go(d: &mut Driver) {
    d.slot = Slot::default();
    let _ = churn_m::k_pull(&mut d.slot, &d.restart_v, 90, d.deferred_label);
    let (matched, line) = churn_m::n_exec(&mut d.slot, &d.restart_v, &d.probe);
    d.out.restart_projection_parity = d.restart_v == d.view
        && line.epoch == d.view.epoch
        && line.seq == d.view.seq
        && line.value == d.view.value
        && line.flags == d.view.flags
        && line.digest == format!("{:016x}", d.view.digest)
        && line.applied_count == d.view.applied_count
        && line.tombstone_count == d.view.tombstone_count
        && line.label == d.deferred_label
        && vtxt(matched) == d.out.paths.direct.verdict;
}

