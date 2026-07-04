use crate::models::{Event, WindowResult};
use std::collections::{HashMap, HashSet};

pub struct SlidingWindowAggregator {
    window_size_ms: i64,
    slide_size_ms: i64,
    // (window_start, name) -> (Vec<f64>, HashSet<String>)
    windows: HashMap<(i64, String), (Vec<f64>, HashSet<String>)>,
}

impl SlidingWindowAggregator {
    pub fn new(window_size_ms: i64, slide_size_ms: i64) -> Self {
        Self {
            window_size_ms,
            slide_size_ms,
            windows: HashMap::new(),
        }
    }

    pub fn add_event(&mut self, event: &Event) {
        // TODO: Map event to all overlapping sliding windows. Deduplicate by event_id.
    }

    pub fn flush_window(&mut self, window_start: i64) -> Vec<WindowResult> {
        // TODO: calculate stats and median
        vec![]
    }
}
