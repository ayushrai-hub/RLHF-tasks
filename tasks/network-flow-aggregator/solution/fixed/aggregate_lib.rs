use nfa_parse::FlowRecord;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowAggregate {
    pub protocol: String,
    pub total_bytes: u64,
    pub total_packets: u64,
    pub flow_count: u64,
    pub unique_pairs: u64,
}

pub fn aggregate_flows(records: &[FlowRecord]) -> Vec<FlowAggregate> {
    let mut proto_map: HashMap<String, FlowAggregate> = HashMap::new();
    let mut pairs: HashMap<String, HashSet<String>> = HashMap::new();
    
    for rec in records {
        let key = rec.protocol.clone();
        let entry = proto_map.entry(key).or_insert(FlowAggregate {
            protocol: rec.protocol.clone(),
            total_bytes: 0,
            total_packets: 0,
            flow_count: 0,
            unique_pairs: 0,
        });
        
        entry.total_bytes += rec.bytes;
        entry.total_packets += rec.packets;
        entry.flow_count += 1;
        
        let pair_key = format!("{}->{}", rec.src_ip, rec.dst_ip);
        pairs.entry(rec.protocol.clone()).or_default().insert(pair_key);
    }
    
    for agg in proto_map.values_mut() {
        agg.unique_pairs = pairs.get(&agg.protocol)
            .map_or(0, |s| s.len() as u64);
    }
    
    proto_map.into_values().collect()
}
