use crate::journal::LoadedReplay;
use crate::replay::ReplayContext;
use crate::tonnage::recorded_tonnage;
use serde_json::{json, Value};

pub fn build_report(
    ctx: &ReplayContext,
    rollback_performed: bool,
    state_generation: u64,
    rollback_reason: Option<&str>,
    snapshot_id: Option<&str>,
    replay: &LoadedReplay,
) -> Value {
    let ledger = &ctx.ledger;
    let bound_dies: Vec<Value> = ledger
        .bound_dies_sorted()
        .into_iter()
        .map(|rec| {
            let mut row = json!({
                "die_id": rec.die_id,
                "checksum_or_digest": if rec.digest_hex.is_empty() {
                    json!(rec.checksum)
                } else {
                    json!(rec.digest_hex)
                },
                "tonnage": rec.tonnage,
                "forge_epoch": rec.forge_epoch,
                "source_format": rec.source_format,
            });
            if let Some(rev) = rec.revision {
                row.as_object_mut()
                    .unwrap()
                    .insert("revision".into(), json!(rev));
            }
            row
        })
        .collect();
    json!({
        "schema_version": 2,
        "ready": !rollback_performed && ledger.die_count() > 0,
        "rollback_performed": rollback_performed,
        "rollback_reason": rollback_reason,
        "scenario_tag": ledger.scenario_tag(),
        "forge_epoch": ledger.forge_epoch(),
        "journal_revision": ledger.journal_revision(),
        "state_generation": state_generation,
        "pack_generation": replay.pack_generation,
        "dies_bound": ledger.die_count(),
        "dies_sealed": ctx.dies_sealed,
        "dies_tombstoned": ctx.dies_tombstoned,
        "tonnage_recorded": recorded_tonnage(ledger),
        "journal_digest_hex": replay.journal_digest,
        "lineage_digest_hex": replay.lineage_digest_hex,
        "die_root_digest_hex": ledger.die_root_digest(),
        "snapshot_id": snapshot_id,
        "ledger_digest_hex": ledger.ledger_digest_hex(),
        "bound_dies": bound_dies,
    })
}

pub fn render_report(body: &Value) -> String {
    serde_json::to_string_pretty(body).unwrap() + "\n"
}
