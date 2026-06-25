use crate::gate::dispatch::{self, m_frame};
use crate::ring::audit;

use super::{vtxt, Driver};

pub fn go(d: &mut Driver) {
    let frame = m_frame(d.direct_label, &d.view);
    let matched = dispatch::direct_probe(&d.view, &frame, &d.probe);
    d.direct_ok = matched;
    d.out.paths.direct.verdict = vtxt(matched);
    d.out.paths.direct.epoch = frame.epoch;
    d.out.paths.direct.seq = frame.seq;
    d.out.paths.direct.value = frame.value;
    d.out.paths.direct.flags = frame.flags;
    d.out.paths.direct.digest = format!("{:016x}", frame.digest);
    d.out.paths.direct.applied_count = frame.applied_count;
    d.out.paths.direct.tombstone_count = frame.tombstone_count;
    let expected = audit::reference_view(d);
    d.out.projection_complete = d.view == expected;
    d.out.epoch_barrier = d.view.epoch == expected.epoch && d.view.flags == expected.flags;
    d.out.revision_tiebreak =
        d.view.value == expected.value && d.view.digest == expected.digest;
    d.out.tombstone_suppression =
        d.view.tombstone_count == expected.tombstone_count
            && d.view.applied_count == expected.applied_count
            && d.view.value == expected.value;
}

