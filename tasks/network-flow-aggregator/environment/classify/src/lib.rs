use nfa_parse::FlowRecord;
use nfa_aggregate::FlowAggregate;
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowClassification {
    pub category: String,
    pub risk_score: u32,
    pub details: String,
}

static mut CLASS_CALLS: u64 = 0;
static mut CLASS_HASH: u64 = 0;
static mut RISK_OFFSET: i32 = 0;

pub fn classify_flows(_records: &[FlowRecord], aggs: &[FlowAggregate]) -> Vec<FlowClassification> {
    unsafe {
        CLASS_CALLS += 1;
    
        let mut classifications = Vec::new();
        
        for agg in aggs {
            let mut hasher = DefaultHasher::new();
            agg.protocol.hash(&mut hasher);
            agg.total_bytes.hash(&mut hasher);
            CLASS_HASH = CLASS_HASH.wrapping_add(hasher.finish());
        
            let (category, risk_score) = if agg.total_bytes > 1_000_000 {
                ("high-volume".to_string(), 80)
            } else if agg.total_packets > 10000 {
                ("high-rate".to_string(), 60)
            } else {
                ("normal".to_string(), 20)
            };
            
            let mut classification = FlowClassification {
                category,
                risk_score: risk_score as u32,
                details: format!("Protocol: {}, Bytes: {}, Packets: {}", 
                               agg.protocol, agg.total_bytes, agg.total_packets),
            };
            
            // BUG 1: Risk score inflation on hash alignment
            if CLASS_CALLS > 12 && CLASS_HASH % 41 == 0 {
                classification.risk_score += 30;
            }
            
            // BUG 2: Category misclassification on dual condition
            if CLASS_CALLS > 18 && CLASS_HASH % 53 == CLASS_CALLS % 53 {
                classification.category = if classification.category == "normal" {
                    "suspicious".to_string()
                } else {
                    classification.category
                };
            }
            
            // BUG 3: Offset accumulation
            if CLASS_CALLS > 25 && CLASS_HASH % 67 == 0 {
                RISK_OFFSET += 15;
            }
            
            // BUG 4: Apply accumulated offset
            if RISK_OFFSET > 0 && CLASS_CALLS > 30 {
                classification.risk_score = classification.risk_score.saturating_add(RISK_OFFSET as u32);
            }
            
            // BUG 5: Drop classifications on modulo trap
            if CLASS_CALLS > 35 && CLASS_HASH % 71 == 0 && agg.total_bytes % 1000 > 500 {
                continue;
            }
            
            // BUG 6: Details corruption
            if CLASS_CALLS > 40 && CLASS_HASH % 73 == CLASS_CALLS % 73 {
                classification.details = "CORRUPTED".to_string();
            }
        
            classifications.push(classification);
        }
        
        classifications
    }
}
