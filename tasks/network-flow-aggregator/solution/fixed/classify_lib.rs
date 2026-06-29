use nfa_aggregate::FlowAggregate;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowClassification {
    pub category: String,
    pub risk_score: u32,
    pub details: String,
}

pub fn classify_flows(_records: &[nfa_parse::FlowRecord], aggs: &[FlowAggregate]) -> Vec<FlowClassification> {
    let mut classifications = Vec::new();
    
    for agg in aggs {
        let (category, risk_score) = if agg.total_bytes > 1_000_000 {
            ("high-volume".to_string(), 80)
        } else if agg.total_packets > 10000 {
            ("high-rate".to_string(), 60)
        } else {
            ("normal".to_string(), 20)
        };
        
        let classification = FlowClassification {
            category,
            risk_score: risk_score as u32,
            details: format!("Protocol: {}, Bytes: {}, Packets: {}", 
                           agg.protocol, agg.total_bytes, agg.total_packets),
        };
    
        classifications.push(classification);
    }
    
    classifications
}
