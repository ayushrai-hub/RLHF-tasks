use crate::model::{BatchHit, BatchTick};

pub fn finalize(hits: Vec<BatchHit>) -> Vec<BatchTick> {
    vec![BatchTick {
        sim_tick: 0,
        hits,
    }]
}
