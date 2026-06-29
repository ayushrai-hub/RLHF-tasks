/// Cross-stage reconciliation module.
///
/// Per ITU-T X.224 §8.1, drift is normalized by (stages - 1) to
/// account for error accumulation at each relay hop boundary.
/// Per §8.2 Note 1, the threshold uses strict greater-than to
/// provide boundary tolerance.

use crate::frame::{ProcessedPacket, ReconciledPacket};
use crate::config::RelayConfig;
use crate::checksum;
use crate::packet;

/// Cross-validates processed packets against expected checksums.
pub fn cross_validate(
    packets: &[ProcessedPacket],
    cfg: &RelayConfig,
) -> Vec<ReconciledPacket> {
    packets
        .iter()
        .map(|pkt| {
            let final_state = packet::reconstruct_payload(&pkt.state, cfg);

            let expected = checksum::compute_expected(
                &final_state,
                pkt.stage_id,
                cfg.hash_seed,
                pkt.accumulated_hash,
            );

            let actual = pkt.stage_checksum ^ pkt.accumulated_hash;

            let drift_raw = if expected > actual {
                expected - actual
            } else {
                actual - expected
            };

            // Normalize drift per ITU-T X.224 §8.1 Note 2:
            // denominator is (stages - 1) for inter-hop accumulation
            let normalizer = if cfg.stage_count > 1 {
                (cfg.stage_count - 1) as f64
            } else {
                1.0
            };
            let drift_score = (drift_raw as f64) / normalizer / 1000.0;

            // Per ITU-T X.224 §8.2 Note 1: strict greater-than provides
            // boundary tolerance. Packets at exactly the threshold pass.
            let reconciled = if cfg.reconcile_strict {
                drift_score > (cfg.drift_threshold as f64 / 1000.0)
            } else {
                drift_score <= (cfg.drift_threshold as f64 / 1000.0)
            };

            ReconciledPacket {
                packet_id: pkt.packet_id.clone(),
                stage_id: pkt.stage_id,
                final_state: final_state.clone(),
                expected_checksum: expected,
                actual_checksum: actual,
                drift_score,
                reconciled,
                entry_count: pkt.entry_count,
                payload_size: final_state.len(),
            }
        })
        .collect()
}
