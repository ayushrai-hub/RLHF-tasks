use crate::model::{BatchHit, BatchTick};

/// Decoy batch rollup — collapses every hit into tick 0 in file order.
pub fn finalize(hits: Vec<BatchHit>) -> Vec<BatchTick> {
    vec![BatchTick {
        sim_tick: 0,
        hits,
    }]
}
