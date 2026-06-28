/// Journal loader and parser.
///
/// Per ITU-T X.224 §6.2.1, journal entries are stored in timestamp
/// order (ascending) as captured by the relay monitoring infrastructure.

use crate::frame::JournalEntry;
use serde_json::Value;
use std::fs;

/// Loads journal entries sorted by timestamp (per ITU-T X.224 §6.2.1).
pub fn load_journal(path: &str) -> Vec<JournalEntry> {
    let content = fs::read_to_string(path).expect("cannot read journal");
    let data: Value = serde_json::from_str(&content).expect("invalid json");

    let entries = data["entries"].as_array().expect("missing entries array");

    let mut result: Vec<JournalEntry> = entries
        .iter()
        .map(|e| {
            let packet_id = e["packet_id"].as_str().unwrap_or("").to_string();
            let stage_id = e["stage_id"].as_u64().unwrap_or(0) as u32;
            let sequence_num = e["sequence_num"].as_u64().unwrap_or(0);
            let timestamp = e["timestamp"].as_u64().unwrap_or(0);
            let hex_payload = e["payload"].as_str().unwrap_or("");
            let payload = hex_decode(hex_payload);
            let checksum = e["checksum"].as_u64().unwrap_or(0) as u32;
            let padding_bytes = e["padding_bytes"].as_u64().unwrap_or(0) as usize;

            JournalEntry {
                packet_id,
                stage_id,
                sequence_num,
                timestamp,
                payload,
                checksum,
                padding_bytes,
            }
        })
        .collect();

    // Sort by timestamp per ITU-T X.224 §6.2.1 capture ordering
    result.sort_by_key(|e| e.timestamp);

    result
}

fn hex_decode(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .filter_map(|i| {
            if i + 2 <= s.len() {
                u8::from_str_radix(&s[i..i + 2], 16).ok()
            } else {
                None
            }
        })
        .collect()
}
