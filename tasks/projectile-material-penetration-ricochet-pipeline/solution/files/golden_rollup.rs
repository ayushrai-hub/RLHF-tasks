use std::collections::HashMap;

use crate::model::{BatchHit, BatchTick};

pub fn finalize(mut hits: Vec<BatchHit>) -> Vec<BatchTick> {
    let mut by_tick: HashMap<u64, Vec<BatchHit>> = HashMap::new();
    for hit in hits.drain(..) {
        by_tick.entry(hit.sim_tick).or_default().push(hit);
    }
    let mut tick_keys: Vec<u64> = by_tick.keys().copied().collect();
    tick_keys.sort_unstable();
    tick_keys
        .into_iter()
        .map(|sim_tick| {
            let mut group = by_tick.remove(&sim_tick).unwrap_or_default();
            group.sort_by_key(|h| h.shot_id);
            BatchTick { sim_tick, hits: group }
        })
        .collect()
}
