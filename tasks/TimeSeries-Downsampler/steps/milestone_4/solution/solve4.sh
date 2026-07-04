#!/usr/bin/env bash
set -euo pipefail

cat > /app/app/src/eviction.rs <<'RSEOF'
use crate::causal::CausalBuffer;
use crate::models::Event;
use std::collections::{HashMap, HashSet};

impl CausalBuffer {
    pub fn evict_over_capacity(&mut self, max_orphans: usize) -> Vec<Event> {
        let mut all_evicted = Vec::new();
        
        loop {
            let mut unique_orphans = HashMap::new();
            for orphans_list in self.orphans.values() {
                for orphan in orphans_list {
                    unique_orphans.insert(orphan.event_id.clone(), orphan.clone());
                }
            }
            
            if unique_orphans.len() <= max_orphans {
                break;
            }
            
            let mut parent_to_children: HashMap<String, Vec<String>> = HashMap::new();
            for orphan in unique_orphans.values() {
                for dep in &orphan.dependency_ids {
                    parent_to_children.entry(dep.clone()).or_default().push(orphan.event_id.clone());
                }
            }
            
            let mut subtree_values = HashMap::new();
            for orphan_id in unique_orphans.keys() {
                subtree_values.insert(orphan_id.clone(), Self::calculate_subtree_value(orphan_id, &unique_orphans, &parent_to_children));
            }
            
            let mut lowest_id = None;
            let mut lowest_val = f64::MAX;
            for (id, val) in &subtree_values {
                if *val < lowest_val {
                    lowest_val = *val;
                    lowest_id = Some(id.clone());
                } else if *val == lowest_val {
                    if let Some(current_lowest) = &lowest_id {
                        if id < current_lowest {
                            lowest_id = Some(id.clone());
                        }
                    } else {
                        lowest_id = Some(id.clone());
                    }
                }
            }
            
            let target_id = lowest_id.unwrap();
            
            let mut to_evict = vec![target_id];
            let mut i = 0;
            while i < to_evict.len() {
                let current = to_evict[i].clone();
                if let Some(children) = parent_to_children.get(&current) {
                    for c in children {
                        if !to_evict.contains(c) {
                            to_evict.push(c.clone());
                        }
                    }
                }
                i += 1;
            }
            
            for id in to_evict {
                if let Some(event) = unique_orphans.remove(&id) {
                    all_evicted.push(event);
                    self.deadletter_ids.insert(id.clone());
                    
                    for list in self.orphans.values_mut() {
                        list.retain(|e| e.event_id != id);
                    }
                }
            }
            
            self.orphans.retain(|_, v| !v.is_empty());
        }
        
        all_evicted
    }

    fn calculate_subtree_value(root_id: &str, orphans: &HashMap<String, Event>, p2c: &HashMap<String, Vec<String>>) -> f64 {
        let mut val = 0.0;
        let mut visited = HashSet::new();
        let mut stack = vec![root_id.to_string()];
        
        while let Some(curr) = stack.pop() {
            if visited.contains(&curr) { continue; }
            visited.insert(curr.clone());
            
            if let Some(event) = orphans.get(&curr) {
                val += event.value;
                if let Some(children) = p2c.get(&curr) {
                    for c in children {
                        stack.push(c.clone());
                    }
                }
            }
        }
        val
    }
}
RSEOF
