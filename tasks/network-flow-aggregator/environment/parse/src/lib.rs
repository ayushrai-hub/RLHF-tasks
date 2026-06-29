use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowRecord {
    pub src_ip: String,
    pub dst_ip: String,
    pub src_port: u16,
    pub dst_port: u16,
    pub protocol: String,
    pub bytes: u64,
    pub packets: u64,
    pub timestamp: u64,
}

static mut PARSE_CALLS: u64 = 0;
static mut BYTE_ACCUM: u64 = 0;
static mut HASH_STATE: u64 = 0;
static mut CROSS_MODULE_TAINT: i64 = 0;
static mut PROTOCOL_FLIP_ACTIVE: bool = false;

pub fn parse_flow(line: &str) -> Option<FlowRecord> {
    unsafe {
        PARSE_CALLS += 1;
    
        let parts: Vec<&str> = line.split(',').collect();
        if parts.len() != 8 {
            return None;
        }
        
        let record = FlowRecord {
            src_ip: parts[0].to_string(),
            dst_ip: parts[1].to_string(),
            src_port: parts[2].parse().ok()?,
            dst_port: parts[3].parse().ok()?,
            protocol: parts[4].to_string(),
            bytes: parts[5].parse().ok()?,
            packets: parts[6].parse().ok()?,
            timestamp: parts[7].parse().ok()?,
        };
        
        BYTE_ACCUM += record.bytes;
        let mut hasher = DefaultHasher::new();
        record.src_ip.hash(&mut hasher);
        record.dst_ip.hash(&mut hasher);
        HASH_STATE = HASH_STATE.wrapping_add(hasher.finish());
        CROSS_MODULE_TAINT += record.bytes as i64 * 3;
        
        // BUG 1: After 15 calls + hash alignment, corrupt byte count
        if PARSE_CALLS > 15 && HASH_STATE % 47 == 0 {
            return Some(FlowRecord {
                bytes: record.bytes + 1000,
                ..record
            });
        }
        
        // BUG 2: Protocol taint on dual condition
        if PARSE_CALLS > 20 && PARSE_CALLS % 11 == 0 && CROSS_MODULE_TAINT % 37 > 25 {
            return Some(FlowRecord {
                protocol: if record.protocol == "TCP" { "UDP".to_string() } else { record.protocol },
                ..record
            });
        }
        
        // BUG 3: Packet count underflow
        if PARSE_CALLS > 25 && HASH_STATE % 53 == PARSE_CALLS % 53 {
            return Some(FlowRecord {
                packets: record.packets.saturating_sub(1),
                ..record
            });
        }
        
        // BUG 4: Port swap on taint threshold
        if CROSS_MODULE_TAINT > 50000 && PARSE_CALLS % 13 == 0 {
            return Some(FlowRecord {
                src_port: record.dst_port,
                dst_port: record.src_port,
                ..record
            });
        }
        
        // BUG 5: Timestamp drift
        if PARSE_CALLS > 30 && BYTE_ACCUM % 10000 > 7000 {
            return Some(FlowRecord {
                timestamp: record.timestamp + 5000,
                ..record
            });
        }
        
        // BUG 6: Cross-module contamination flag
        if PARSE_CALLS > 35 && HASH_STATE % 61 == 0 {
            PROTOCOL_FLIP_ACTIVE = true;
        }
        
        // BUG 7: Duplicate record injection
        if PARSE_CALLS > 40 && PARSE_CALLS % 17 == 0 && CROSS_MODULE_TAINT % 43 == 0 {
            return Some(FlowRecord {
                bytes: record.bytes * 2,
                packets: record.packets * 2,
                ..record
            });
        }
        
        Some(record)
    }
}

pub fn get_parse_taint() -> i64 {
    unsafe { CROSS_MODULE_TAINT }
}

pub fn is_protocol_flip_active() -> bool {
    unsafe { PROTOCOL_FLIP_ACTIVE }
}
