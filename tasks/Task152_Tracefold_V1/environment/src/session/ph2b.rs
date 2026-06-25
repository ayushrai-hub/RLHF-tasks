use crate::ring::version::rebuild;

use super::Driver;

pub fn go(d: &mut Driver) {
    d.view = rebuild(
        d.base_epoch,
        d.base_seq,
        d.base_value,
        d.base_flags,
        d.lane_id,
        &d.raw.patches,
    );
}

