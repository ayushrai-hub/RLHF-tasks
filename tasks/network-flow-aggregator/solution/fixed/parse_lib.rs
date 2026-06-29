use serde::{Deserialize, Serialize};

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

pub fn parse_flow(line: &str) -> Option<FlowRecord> {
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
    
    Some(record)
}

pub fn get_parse_taint() -> i64 {
    0
}

pub fn is_protocol_flip_active() -> bool {
    false
}
