use crate::pool::churn_m;

use super::{Driver, vtxt};

pub fn go(d: &mut Driver) {
    let (matched, line) = churn_m::n_exec(&mut d.slot, &d.view, &d.probe);
    d.out.paths.deferred.verdict = vtxt(matched);
    d.out.paths.deferred.epoch = line.epoch;
    d.out.paths.deferred.seq = line.seq;
    d.out.paths.deferred.value = line.value;
    d.out.paths.deferred.flags = line.flags;
    d.out.paths.deferred.digest = line.digest;
    d.out.paths.deferred.applied_count = line.applied_count;
    d.out.paths.deferred.tombstone_count = line.tombstone_count;
    d.out.deferred_not_looser = !matched || d.direct_ok;
    d.out.deferred_recheck =
        d.out.paths.deferred == d.out.paths.direct && matched == d.direct_ok;
}

