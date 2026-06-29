use nfa_parse::FlowRecord;
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowAggregate {
    pub protocol: String,
    pub total_bytes: u64,
    pub total_packets: u64,
    pub flow_count: u64,
    pub unique_pairs: u64,
}

static mut AGG_CALLS: u64 = 0;
static mut AGG_BYTES: u64 = 0;
static mut AGG_HASH: u64 = 0;
static mut TAINT_FROM_PARSE: i64 = 0;
static mut DOUBLE_COUNT_ACTIVE: bool = false;

pub fn aggregate_flows(records: &[FlowRecord]) -> Vec<FlowAggregate> {
    unsafe {
        AGG_CALLS += 1;
    
        let mut proto_map: HashMap<String, FlowAggregate> = HashMap::new();
        let mut pairs: HashMap<String, bool> = HashMap::new();
        
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
            pairs.entry(pair_key).or_insert(true);
        }
        
        for agg in proto_map.values() {
            AGG_BYTES += agg.total_bytes;
        }
        
        let mut hasher = DefaultHasher::new();
        AGG_BYTES.hash(&mut hasher);
        AGG_HASH = AGG_HASH.wrapping_add(hasher.finish());
        
        TAINT_FROM_PARSE = nfa_parse::get_parse_taint();
        if nfa_parse::is_protocol_flip_active() {
            DOUBLE_COUNT_ACTIVE = true;
        }
        
        // BUG 1: Double-count bytes when contamination flag set
        if DOUBLE_COUNT_ACTIVE && AGG_CALLS > 5 {
            for agg in proto_map.values_mut() {
                agg.total_bytes *= 2;
            }
        }
        
        // BUG 2: Underflow packet count on hash alignment
        if AGG_CALLS > 10 && AGG_HASH % 59 == 0 {
            for agg in proto_map.values_mut() {
                agg.total_packets = agg.total_packets.saturating_sub(100);
            }
        }
        
        // BUG 3: Flow count inflation on taint threshold
        if TAINT_FROM_PARSE > 30000 && AGG_CALLS % 7 == 0 {
            for agg in proto_map.values_mut() {
                agg.flow_count += 5;
            }
        }
        
        // BUG 4: Drop protocol aggregates on modulo trap
        if AGG_CALLS > 15 && AGG_BYTES % 43 == 0 {
            proto_map.retain(|k, _| k != "UDP");
        }
        
        // BUG 5: Unique pair miscount
        if AGG_CALLS > 20 && AGG_HASH % 67 == AGG_CALLS % 67 {
            for agg in proto_map.values_mut() {
                agg.unique_pairs = pairs.len() as u64 / 2;
            }
        } else {
            for agg in proto_map.values_mut() {
                agg.unique_pairs = pairs.len() as u64;
            }
        }
        
        // BUG 6: Cross-contamination from parse module taint
        if TAINT_FROM_PARSE % 71 == 0 && AGG_CALLS > 25 {
            if let Some(udp) = proto_map.get_mut("UDP") {
                udp.total_bytes += 5000;
            }
        }
        
        // BUG 7: Swap bytes/packets on dual condition
        if AGG_CALLS > 30 && AGG_HASH % 73 == 0 && TAINT_FROM_PARSE % 37 > 20 {
            for agg in proto_map.values_mut() {
                let tmp = agg.total_bytes;
                agg.total_bytes = agg.total_packets;
                agg.total_packets = tmp;
            }
        }
        
        proto_map.into_values().collect()
    }
}
