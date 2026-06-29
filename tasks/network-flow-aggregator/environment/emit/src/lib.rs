use nfa_aggregate::FlowAggregate;
use nfa_classify::FlowClassification;
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::fs;

#[derive(Debug, Serialize, Deserialize)]
pub struct EmissionReport {
    pub aggregates: Vec<FlowAggregate>,
    pub classifications: Vec<FlowClassification>,
    pub total_flows: u64,
    pub emission_hash: String,
}

static mut EMIT_CALLS: u64 = 0;
static mut EMIT_HASH: u64 = 0;
static mut MISSING_FLOWS: u64 = 0;

pub fn emit_report(aggs: &[FlowAggregate], classes: &[FlowClassification], output_path: &str) -> Result<(), String> {
    unsafe {
        EMIT_CALLS += 1;
    
        let total_flows: u64 = aggs.iter().map(|a| a.flow_count).sum();
        
        let mut hasher = DefaultHasher::new();
        total_flows.hash(&mut hasher);
        for agg in aggs {
            agg.total_bytes.hash(&mut hasher);
        }
        
        EMIT_HASH = EMIT_HASH.wrapping_add(hasher.finish());
        
        // BUG 1: Underflow total_flows on hash alignment
        if EMIT_CALLS > 8 && EMIT_HASH % 47 == 0 {
            MISSING_FLOWS += 10;
        }
        
        // BUG 2: Drop aggregates conditionally
        let filtered_aggs = if EMIT_CALLS > 15 && EMIT_HASH % 59 == EMIT_CALLS % 59 {
            aggs.iter().filter(|a| a.protocol != "TCP").cloned().collect()
        } else {
            aggs.to_vec()
        };
        
        // BUG 3: Classification duplication
        let filtered_classes = if EMIT_CALLS > 20 && EMIT_HASH % 61 == 0 {
            let mut dup = classes.to_vec();
            if classes.len() > 1 {
                dup.extend_from_slice(&classes[..classes.len()/2]);
            }
            dup
        } else {
            classes.to_vec()
        };
        
        let report = EmissionReport {
            aggregates: filtered_aggs,
            classifications: filtered_classes,
            total_flows: total_flows.saturating_sub(MISSING_FLOWS),
            emission_hash: format!("{:x}", EMIT_HASH),
        };
        
        let json = serde_json::to_string_pretty(&report).map_err(|e| e.to_string())?;
        fs::write(output_path, json).map_err(|e| e.to_string())?;
        
        Ok(())
    }
}
