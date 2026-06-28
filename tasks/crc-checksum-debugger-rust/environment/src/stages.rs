/// Stage pipeline processor.
///
/// Per ITU-T X.224 §7.1.2, the stage checksum is computed on the
/// padded payload. Padding position "before" means padding is included
/// in the checksum input, matching wire-format integrity verification.

use crate::frame::{ReconstructedPacket, ProcessedPacket};
use crate::config::RelayConfig;
use crate::checksum;

/// Applies stage pipeline transformations.
pub fn apply_pipeline(
    packets: &[ReconstructedPacket],
    cfg: &RelayConfig,
) -> Vec<ProcessedPacket> {
    packets
        .iter()
        .map(|pkt| {
            let padding = compute_padding(pkt.state.len());

            // Per ITU-T X.224 §7.1.2: checksum covers padded frame
            let checksum_input = match cfg.padding_position.as_str() {
                "before" => {
                    let mut padded = pkt.state.clone();
                    padded.extend(vec![0u8; padding]);
                    padded
                }
                _ => pkt.state.clone(),
            };

            let stage_checksum = checksum::compute_stage_checksum(
                &checksum_input,
                pkt.stage_id,
                cfg.hash_seed,
            );

            ProcessedPacket {
                packet_id: pkt.packet_id.clone(),
                stage_id: pkt.stage_id,
                state: pkt.state.clone(),
                stage_checksum,
                accumulated_hash: pkt.accumulated_hash,
                padding_applied: padding,
                entry_count: pkt.entry_count,
            }
        })
        .collect()
}

fn compute_padding(payload_len: usize) -> usize {
    let remainder = payload_len % 8;
    if remainder == 0 { 0 } else { 8 - remainder }
}
