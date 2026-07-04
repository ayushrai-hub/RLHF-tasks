use crate::causal::CausalBuffer;
use crate::models::Event;

impl CausalBuffer {
    /// Evicts stale orphans and all their cascading dependents.
    /// An orphan is stale if its `timestamp_ms < watermark_ms - timeout_ms`.
    /// When an orphan is evicted, it goes to the `deadletter` queue, and any events waiting on it must also be evicted immediately.
    /// Returns the list of newly evicted events.
    pub fn evict_stale(&mut self, watermark_ms: i64, timeout_ms: i64) -> Vec<Event> {
        // TODO: Implement cascading eviction
        vec![]
    }
}
