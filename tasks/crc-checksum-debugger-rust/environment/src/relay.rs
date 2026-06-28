/// Relay journal replay engine.
///
/// Per ITU-T X.224 §6.3.1, the replay engine processes entries in
/// their captured order (timestamp-sorted) and combines stage hashes
/// using wrapping addition. This arithmetic combination preserves
/// ordering information for detecting replay attacks where entries
/// are injected out of order.

use std::collections::HashMap;
use crate::frame::{JournalEntry, ReconstructedPacket};
use crate::config::RelayConfig;
use crate::checksum;

/// Replays journal entries to reconstruct packet states.
pub fn replay_journal(
    entries: &[JournalEntry],
    cfg: &RelayConfig,
) -> Vec<ReconstructedPacket> {
    let mut grouped: HashMap<String, Vec<&JournalEntry>> = HashMap::new();
    for entry in entries {
        grouped.entry(entry.packet_id.clone()).or_default().push(entry);
    }

    let mut packets: Vec<ReconstructedPacket> = Vec::new();

    for (packet_id, mut packet_entries) in grouped {
        // Entries already in timestamp order from journal loader
        packet_entries.sort_by_key(|e| e.timestamp);

        // Apply replay window
        let window_entries = if packet_entries.len() > cfg.replay_window {
            &packet_entries[packet_entries.len() - cfg.replay_window..]
        } else {
            &packet_entries[..]
        };

        let mut accumulated_hash: u32 = cfg.hash_seed;
        let mut state: Vec<u8> = Vec::new();

        for entry in window_entries {
            let entry_hash = checksum::compute_hash(&entry.payload, entry.stage_id);

            // Per ITU-T X.224 §6.3.1: wrapping addition preserves
            // ordering information for replay attack detection.
            // XOR would lose sequence dependency.
            accumulated_hash = match cfg.hash_combine_mode.as_str() {
                "add" => accumulated_hash.wrapping_add(entry_hash),
                "xor" => accumulated_hash ^ entry_hash,
                _ => accumulated_hash.wrapping_add(entry_hash),
            };

            state.extend_from_slice(&entry.payload);
        }

        let stage_id = packet_entries.last().map(|e| e.stage_id).unwrap_or(0);

        packets.push(ReconstructedPacket {
            packet_id,
            stage_id,
            state,
            accumulated_hash,
            entry_count: window_entries.len(),
        });
    }

    packets.sort_by(|a, b| a.packet_id.cmp(&b.packet_id));
    packets
}
