use crate::models::{Event, WindowResult};
use std::collections::HashMap;

pub struct TumblingWindowAggregator {
    window_size_ms: i64,
    // (window_start, name) -> ...
    windows: HashMap<(i64, String), Vec<f64>>,
}

impl TumblingWindowAggregator {
    pub fn new(window_size_ms: i64) -> Self {
        Self {
            window_size_ms,
            windows: HashMap::new(),
        }
    }

    pub fn add_event(&mut self, event: &Event) {
        // TODO: add event to window buffer
    }

    pub fn flush_window(&mut self, window_start: i64) -> Vec<WindowResult> {
        // TODO: compute count, min, max, avg, and median
        vec![]
    }
}
