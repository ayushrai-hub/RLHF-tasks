/// Report generation module.

use serde_json::Value;
use crate::frame::{ReconciledPacket, AuditSummary};

pub fn build_report(packets: Vec<ReconciledPacket>, summary: AuditSummary) -> Value {
    let mut sorted = packets;
    sorted.sort_by(|a, b| {
        a.stage_id.cmp(&b.stage_id)
            .then_with(|| a.packet_id.cmp(&b.packet_id))
    });

    let packet_entries: Vec<Value> = sorted
        .iter()
        .map(|p| {
            serde_json::json!({
                "packet_id": p.packet_id,
                "stage_id": p.stage_id,
                "expected_checksum": format!("0x{:08X}", p.expected_checksum),
                "actual_checksum": format!("0x{:08X}", p.actual_checksum),
                "drift_score": format!("{:.6}", p.drift_score),
                "reconciled": p.reconciled,
                "payload_size": p.payload_size,
                "entry_count": p.entry_count,
            })
        })
        .collect();

    serde_json::json!({
        "packets": packet_entries,
        "summary": {
            "total_packets": summary.total_packets,
            "reconciled_pass": summary.reconciled_pass,
            "reconciled_fail": summary.reconciled_fail,
            "avg_drift": format!("{:.6}", summary.avg_drift),
            "max_drift": format!("{:.6}", summary.max_drift),
            "stages_active": summary.stages_active,
            "total_entries_replayed": summary.total_entries_replayed,
            "packets_truncated": summary.packets_truncated,
        }
    })
}
