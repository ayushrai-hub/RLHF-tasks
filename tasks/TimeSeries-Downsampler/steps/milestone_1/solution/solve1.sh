#!/usr/bin/env bash
set -euo pipefail

cat > /app/app/src/parser.rs <<'RSEOF'
use crate::models::Event;

fn decode_b64(input: &str) -> Option<Vec<u8>> {
    let mut buffer = Vec::new();
    let mut accum = 0u32;
    let mut bits = 0;
    
    for c in input.chars() {
        if c == '=' { break; }
        let val = match c {
            'A'..='Z' => c as u32 - 'A' as u32,
            'a'..='z' => c as u32 - 'a' as u32 + 26,
            '0'..='9' => c as u32 - '0' as u32 + 52,
            '+' => 62,
            '/' => 63,
            _ => continue,
        };
        accum = (accum << 6) | val;
        bits += 6;
        if bits >= 8 {
            bits -= 8;
            buffer.push((accum >> bits) as u8);
        }
    }
    Some(buffer)
}

pub fn parse_event(line: &str) -> Option<Event> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;
    let mut chars = line.trim().chars();

    for c in chars {
        match c {
            '"' => in_quotes = !in_quotes,
            '|' if !in_quotes => {
                parts.push(current.clone());
                current.clear();
            }
            _ => current.push(c),
        }
    }
    parts.push(current);

    if parts.len() < 4 || parts.len() > 5 {
        return None;
    }
    
    let timestamp_ms = parts[0].parse::<i64>().ok()?;
    let event_id = parts[1].to_string();
    let name = parts[2].to_string();
    
    let value = if parts[3].starts_with("b64:") {
        let b64_str = &parts[3][4..];
        let bytes = decode_b64(b64_str)?;
        if bytes.len() != 8 { return None; }
        let mut arr = [0u8; 8];
        arr.copy_from_slice(&bytes[..8]);
        f64::from_le_bytes(arr)
    } else {
        parts[3].parse::<f64>().ok()?
    };
    
    let dependency_ids = if parts.len() == 5 && !parts[4].is_empty() {
        parts[4].split(',').map(|s| s.to_string()).collect()
    } else {
        Vec::new()
    };
    
    Some(Event {
        timestamp_ms,
        event_id,
        name,
        value,
        dependency_ids,
    })
}
RSEOF

cat > /app/app/src/tumbling.rs <<'RSEOF'
use crate::models::{Event, WindowResult};
use std::collections::HashMap;

pub struct TumblingWindowAggregator {
    window_size_ms: i64,
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
        let window_start = (event.timestamp_ms / self.window_size_ms) * self.window_size_ms;
        let key = (window_start, event.name.clone());
        self.windows.entry(key).or_default().push(event.value);
    }

    pub fn flush_window(&mut self, window_start: i64) -> Vec<WindowResult> {
        let mut results = Vec::new();
        let mut keys_to_remove = Vec::new();
        
        for (key, vals) in self.windows.iter_mut() {
            if key.0 == window_start {
                if vals.is_empty() { continue; }
                let count = vals.len();
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
