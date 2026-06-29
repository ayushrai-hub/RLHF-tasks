/// Metrics computation for audit summary.

use crate::frame::{ReconciledPacket, AuditSummary};
use crate::config::RelayConfig;
use std::collections::HashSet;

/// Computes aggregate metrics from reconciled packets.
pub fn compute_metrics(
    packets: &[ReconciledPacket],
    cfg: &RelayConfig,
) -> AuditSummary {
    let total_packets = packets.len() as u32;
    let reconciled_pass = packets.iter().filter(|p| p.reconciled).count() as u32;
    let reconciled_fail = packets.iter().filter(|p| !p.reconciled).count() as u32;

    let drift_scores: Vec<f64> = packets.iter().map(|p| p.drift_score).collect();
    let avg_drift = if !drift_scores.is_empty() {
        drift_scores.iter().sum::<f64>() / drift_scores.len() as f64
    } else {
        0.0
    };
    let max_drift = drift_scores.iter().cloned().fold(0.0_f64, f64::max);

    let stages_active = packets
        .iter()
        .map(|p| p.stage_id)
        .collect::<HashSet<_>>()
        .len() as u32;

    let total_entries_replayed = packets.iter().map(|p| p.entry_count as u32).sum();

    let packets_truncated = packets
        .iter()
        .filter(|p| p.entry_count >= cfg.replay_window)
        .count() as u32;

    AuditSummary {
        total_packets,
        reconciled_pass,
        reconciled_fail,
        avg_drift,
        max_drift,
        stages_active,
        total_entries_replayed,
        packets_truncated,
    }
}
