use crate::pool::churn_m;
use crate::pool::slot::Slot;

use super::Driver;

pub fn go(d: &mut Driver) {
    d.slot = Slot::default();
    let _ = churn_m::k_pull(&mut d.slot, &d.view, 10, d.direct_label);
    let _ = churn_m::n_exec(&mut d.slot, &d.view, &d.probe);
    let _ = churn_m::k_pull(&mut d.slot, &d.view, 11, d.deferred_label);
    let (_matched, line) = churn_m::n_exec(&mut d.slot, &d.view, &d.probe);
    d.out.worker_reuse_safe = line.label == d.deferred_label && d.slot.run == d.deferred_label;
    d.out.line_source.label = line.label;
    d.out.line_source.ok = line.label == d.slot.run && line.label == d.deferred_label;
}

