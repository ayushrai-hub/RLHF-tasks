use crate::models::Event;
use std::collections::{HashMap, HashSet};

pub struct CausalBuffer {
    // Stores the event_ids of all successfully processed events
    pub processed_ids: HashSet<String>,
    // Maps a dependency_id to a list of orphan events waiting for it
    pub orphans: HashMap<String, Vec<Event>>,
    // Stores the ordered list of successfully processed events ready for aggregation
    pub aggregated_events: Vec<Event>,
}

impl CausalBuffer {
    pub fn new() -> Self {
        Self {
            processed_ids: HashSet::new(),
            orphans: HashMap::new(),
            aggregated_events: Vec::new(),
        }
    }

    /// Process an event. 
    /// If its dependency is unmet, buffer it in `orphans`.
    /// If met (or None), add to `aggregated_events`, mark as processed, and recursively process any orphans waiting on this event.
    pub fn process_event(&mut self, event: Event) {
        // TODO: Implement causal buffering and recursive unblocking.
    }
}
