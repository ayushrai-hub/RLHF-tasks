use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

use crate::agg::{BranchAcc, PartialFrame};

pub fn digest_probe_h5(frame: &PartialFrame) -> u64 {
    let mut h = DefaultHasher::new();
    for b in &frame.branches {
        b.branch_id.hash(&mut h);
        (b.acc.sum as f32).to_bits().hash(&mut h);
        b.acc.count.hash(&mut h);
    }
    h.finish()
}

pub fn branch_digest(b: &BranchAcc) -> u64 {
    let mut h = DefaultHasher::new();
    b.branch_id.hash(&mut h);
    (b.acc.sum as f32).to_bits().hash(&mut h);
    b.acc.count.hash(&mut h);
    h.finish()
}
