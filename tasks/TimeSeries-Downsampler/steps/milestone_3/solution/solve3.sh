#!/usr/bin/env bash
set -euo pipefail

cat > /app/app/src/causal.rs <<'RSEOF'
use crate::models::Event;
use std::collections::{HashMap, HashSet};

pub struct CausalBuffer {
    pub processed_ids: HashSet<String>,
    pub orphans: HashMap<String, Vec<Event>>,
    pub aggregated_events: Vec<Event>,
    pub deadletter_ids: HashSet<String>,
}

impl CausalBuffer {
    pub fn new() -> Self {
        Self {
            processed_ids: HashSet::new(),
            orphans: HashMap::new(),
            aggregated_events: Vec::new(),
            deadletter_ids: HashSet::new(),
        }
    }

    fn has_cycle(event_id: &str, start_deps: &[String], orphans: &HashMap<String, Vec<Event>>) -> bool {
        let mut visited = HashSet::new();
        let mut stack: Vec<String> = start_deps.to_vec();
        
        while let Some(current) = stack.pop() {
            if current == event_id { return true; }
            if visited.contains(&current) { continue; }
            visited.insert(current.clone());
            
            for (k, v) in orphans.iter() {
                if v.iter().any(|e| e.event_id == current) {
                    stack.push(k.clone());
                }
            }
        }
        false
    }

    pub fn process_event(&mut self, event: Event) {
        if event.dependency_ids.iter().any(|d| self.deadletter_ids.contains(d)) {
            self.deadletter_ids.insert(event.event_id);
            return;
        }

        if Self::has_cycle(&event.event_id, &event.dependency_ids, &self.orphans) {
            self.deadletter_ids.insert(event.event_id);
            return;
        }

        let missing: Vec<String> = event.dependency_ids.iter()
            .filter(|d| !self.processed_ids.contains(*d))
            .cloned()
            .collect();

        if !missing.is_empty() {
            for m in missing {
                self.orphans.entry(m).or_default().push(event.clone());
            }
            return;
        }

        let event_id = event.event_id.clone();
        self.aggregated_events.push(event);
        self.processed_ids.insert(event_id.clone());

        if let Some(unblocked) = self.orphans.remove(&event_id) {
            let mut ready = Vec::new();
            for orphan in unblocked {
                if orphan.dependency_ids.iter().all(|d| self.processed_ids.contains(d)) {
                    if !self.processed_ids.contains(&orphan.event_id) {
                        ready.push(orphan);
                    }
                }
            }
            
            for r in ready {
                // Clean up from other lists to avoid stale duplicates
                for d in &r.dependency_ids {
                    if let Some(list) = self.orphans.get_mut(d) {
                        list.retain(|e| e.event_id != r.event_id);
                    }
                }
                self.process_event(r);
            }
        }
    }
}
RSEOF
