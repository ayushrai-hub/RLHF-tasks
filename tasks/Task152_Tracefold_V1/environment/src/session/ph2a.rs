use crate::pool::churn_m;

use super::Driver;

pub fn go(d: &mut Driver) {
    let _ = churn_m::k_pull(&mut d.slot, &d.view, 401, d.deferred_label);
}

