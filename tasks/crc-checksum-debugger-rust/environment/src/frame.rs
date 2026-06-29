/// Data frame definitions for relay audit.

#[derive(Debug, Clone)]
pub struct JournalEntry {
    pub packet_id: String,
    pub stage_id: u32,
    pub sequence_num: u64,
    pub timestamp: u64,
    pub payload: Vec<u8>,
    pub checksum: u32,
    pub padding_bytes: usize,
}

#[derive(Debug, Clone)]
pub struct ReconstructedPacket {
    pub packet_id: String,
    pub stage_id: u32,
    pub state: Vec<u8>,
    pub accumulated_hash: u32,
    pub entry_count: usize,
}

#[derive(Debug, Clone)]
pub struct ProcessedPacket {
    pub packet_id: String,
    pub stage_id: u32,
    pub state: Vec<u8>,
    pub stage_checksum: u32,
    pub accumulated_hash: u32,
    pub padding_applied: usize,
    pub entry_count: usize,
}

#[derive(Debug, Clone)]
pub struct ReconciledPacket {
    pub packet_id: String,
    pub stage_id: u32,
    pub final_state: Vec<u8>,
    pub expected_checksum: u32,
    pub actual_checksum: u32,
    pub drift_score: f64,
    pub reconciled: bool,
    pub entry_count: usize,
    pub payload_size: usize,
}

#[derive(Debug, Clone)]
pub struct AuditSummary {
    pub total_packets: u32,
    pub reconciled_pass: u32,
    pub reconciled_fail: u32,
    pub avg_drift: f64,
    pub max_drift: f64,
    pub stages_active: u32,
    pub total_entries_replayed: u32,
    pub packets_truncated: u32,
}
