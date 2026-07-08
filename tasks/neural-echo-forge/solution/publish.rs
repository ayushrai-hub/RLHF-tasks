use std::fs;

use serde_json::json;
use sha2::{Digest, Sha256};

use crate::export::index_builder;
use crate::ingest::pipeline::{MemoryRecord, Snapshot};
use crate::staging::reconcile;
use crate::staging::staging_ledger::{self, STAGING_PATH};

const RECORDS_PATH: &str = "/app/output/memory-records.json";
const INDEX_PATH: &str = "/app/output/retrieval-index.json";
const AUDIT_PATH: &str = "/app/output/memory-audit.json";
const SNAPSHOT_PATH: &str = "/app/state/memory-snapshot.json";

fn prior_export_generation() -> u32 {
    if let Ok(text) = fs::read_to_string(AUDIT_PATH) {
        if let Ok(val) = serde_json::from_str::<serde_json::Value>(&text) {
            return val
                .get("export_generation")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as u32;
        }
    }
    0
}

fn export_quota(active: &[MemoryRecord], export_mode: &str) -> Vec<MemoryRecord> {
    use std::collections::BTreeMap;
    let mut grouped: BTreeMap<(String, String), Vec<MemoryRecord>> = BTreeMap::new();
    for rec in active {
        grouped
            .entry((rec.subject.clone(), rec.predicate.clone()))
            .or_default()
            .push(rec.clone());
    }
    let mut records = Vec::new();
    for ((_subj, _pred), mut group) in grouped {
        group.sort_by(|a, b| {
            if export_mode == "open" {
                b.confidence
                    .partial_cmp(&a.confidence)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then(b.anchor_ms.cmp(&a.anchor_ms))
                    .then(b.memory_id.cmp(&a.memory_id))
            } else {
                b.anchor_ms
                    .cmp(&a.anchor_ms)
                    .then(
                        b.confidence
                            .partial_cmp(&a.confidence)
                            .unwrap_or(std::cmp::Ordering::Equal),
                    )
                    .then(b.memory_id.cmp(&a.memory_id))
            }
        });
        if let Some(winner) = group.into_iter().next() {
            records.push(winner);
        }
    }
    records.sort_by(|a, b| {
        a.subject
            .cmp(&b.subject)
            .then(a.predicate.cmp(&b.predicate))
            .then(a.memory_id.cmp(&b.memory_id))
    });
    records
}

pub fn write_exports(snapshot: &Snapshot) -> Result<(), String> {
    fs::create_dir_all("/app/output").map_err(|e| e.to_string())?;

    let staging = staging_ledger::read_staging_ledger()?;
    if staging.staging_seq != snapshot.snapshot_seq {
        return Err("staging ledger seq mismatch".into());
    }

    let report = reconcile::read_reconcile_report()?;
    let staging_digest = staging_ledger::digest_staging_bytes(STAGING_PATH)?;
    if report.snapshot_seq != snapshot.snapshot_seq {
        return Err("reconcile report snapshot seq mismatch".into());
    }
    if report.staging_digest_sha256 != staging_digest {
        return Err("reconcile report staging digest mismatch".into());
    }
    if report.ingest_fingerprint != snapshot.ingest_fingerprint {
        return Err("reconcile report fingerprint mismatch".into());
    }
    if report.candidate_digest_sha256 != staging.candidate_digest_sha256 {
        return Err("reconcile report candidate digest mismatch".into());
    }
    if !report.fingerprint_valid {
        return Err("reconcile report fingerprint invalid".into());
    }

    let records = export_quota(&snapshot.active_memories, &staging.export_mode);
    let records_doc = json!({
        "snapshot_seq": snapshot.snapshot_seq,
        "reference_anchor_ms": snapshot.reference_anchor_ms,
        "records": records,
    });

    let index = index_builder::build_retrieval_index(&records);

    let snap_bytes = fs::read(SNAPSHOT_PATH).map_err(|e| e.to_string())?;
    let snap_digest = format!("{:x}", Sha256::digest(&snap_bytes));

    let audit = json!({
        "snapshot_digest_sha256": snap_digest,
        "staging_digest_sha256": staging_digest,
        "export_generation": prior_export_generation() + 1,
        "active_staged": snapshot.active_memories.len(),
        "vault_staged": snapshot.retention_vault.len(),
        "superseded_staged": snapshot.superseded_memories.len(),
        "exported_records": records.len(),
        "lines_skipped": snapshot.lines_skipped,
    });

    fs::write(
        RECORDS_PATH,
        format!(
            "{}\n",
            serde_json::to_string_pretty(&records_doc).map_err(|e| e.to_string())?
        ),
    )
    .map_err(|e| e.to_string())?;
    fs::write(
        INDEX_PATH,
        format!("{}\n", serde_json::to_string_pretty(&index).map_err(|e| e.to_string())?),
    )
    .map_err(|e| e.to_string())?;
    fs::write(
        AUDIT_PATH,
        format!("{}\n", serde_json::to_string_pretty(&audit).map_err(|e| e.to_string())?),
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
