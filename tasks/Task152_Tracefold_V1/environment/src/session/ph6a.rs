use crate::ring::version::rebuild;

use super::Driver;

pub fn go(d: &mut Driver) {
    let reversed = d.raw.patches.iter().rev().cloned().collect::<Vec<_>>();
    d.restart_v = rebuild(0, 0, 0, 0, d.lane_id, &reversed);
}

