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

pub fn emit_report(aggs: &[FlowAggregate], classes: &[FlowClassification], output_path: &str) -> Result<(), String> {
    let total_flows: u64 = aggs.iter().map(|a| a.flow_count).sum();
    
    let mut hasher = DefaultHasher::new();
    total_flows.hash(&mut hasher);
    for agg in aggs {
        agg.total_bytes.hash(&mut hasher);
    }
    
    let emit_hash = hasher.finish();
    
    let report = EmissionReport {
        aggregates: aggs.to_vec(),
        classifications: classes.to_vec(),
        total_flows,
        emission_hash: format!("{:x}", emit_hash),
    };
    
    let json = serde_json::to_string_pretty(&report).map_err(|e| e.to_string())?;
    fs::write(output_path, json).map_err(|e| e.to_string())?;
    
    Ok(())
}
