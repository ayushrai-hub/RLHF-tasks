#!/usr/bin/env bash
set -euo pipefail

cat > /app/app/src/sliding.rs <<'RSEOF'
use crate::models::{Event, WindowResult};
use std::collections::HashMap;

pub struct SlidingWindowAggregator {
    window_size_ms: i64,
    slide_size_ms: i64,
    windows: HashMap<(i64, String), HashMap<String, f64>>,
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
        let mut w_start = (event.timestamp_ms / self.slide_size_ms) * self.slide_size_ms;
        let mut min_start = w_start - self.window_size_ms + self.slide_size_ms;
        min_start = (min_start / self.slide_size_ms) * self.slide_size_ms;

        let mut current_start = min_start;
        while current_start <= event.timestamp_ms {
            if current_start + self.window_size_ms > event.timestamp_ms {
                let key = (current_start, event.name.clone());
                let entry = self.windows.entry(key).or_insert_with(HashMap::new);
                
                if let Some(existing) = entry.get_mut(&event.event_id) {
                    *existing = f64::from_bits(existing.to_bits() ^ event.value.to_bits());
                } else {
                    entry.insert(event.event_id.clone(), event.value);
                }
            }
            current_start += self.slide_size_ms;
        }
    }

    pub fn flush_window(&mut self, window_start: i64) -> Vec<WindowResult> {
        let mut results = Vec::new();
        let mut keys_to_remove = Vec::new();
        
        for (key, val) in self.windows.iter_mut() {
            if key.0 == window_start {
                if val.is_empty() { continue; }
                let count = val.len();
                let mut vals: Vec<f64> = val.values().copied().collect();
                
                let mut sum = 0.0;
                for &v in vals.iter() { sum += v; }
                let avg = sum / (count as f64);
                
                vals.sort_by(|a, b| a.partial_cmp(b).unwrap());
                let min = vals[0];
                let max = vals[count - 1];
                
                let median = if count % 2 == 1 {
                    vals[count / 2]
                } else {
                    let mid = count / 2;
                    (vals[mid - 1] + vals[mid]) / 2.0
                };

                results.push(WindowResult {
                    window_start_ms: key.0,
                    window_end_ms: key.0 + self.window_size_ms,
                    name: key.1.clone(),
                    count,
                    min,
                    max,
                    avg,
                    median,
                });
                keys_to_remove.push(key.clone());
            }
        }
        
        for key in keys_to_remove {
            self.windows.remove(&key);
        }
        
        results
    }
}
RSEOF
