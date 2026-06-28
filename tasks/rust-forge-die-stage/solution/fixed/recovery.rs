use crate::journal::load_replay;
use crate::ledger::ForgeLedger;
use crate::replay::ReplayContext;
use crate::state::quarantine_state;
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

pub struct RecoveryOutcome {
    pub ledger: ForgeLedger,
    pub rollback: bool,
    pub rollback_reason: Option<String>,
    pub snapshot_id: Option<String>,
    pub warnings: Vec<String>,
    pub ctx: ReplayContext,
}

pub fn replay_with_recovery(
    input_path: &str,
    die_root: &str,
    snapshot_path: &str,
    log_path: &str,
    state_dir: Option<&str>,
) -> Result<RecoveryOutcome, String> {
    let replay = load_replay(input_path, die_root, snapshot_path)?;
    let journal_digest = replay.journal_digest.clone();
    let lineage_digest_hex = replay.lineage_digest_hex.clone();
    let raw = fs::read_to_string(snapshot_path).map_err(|e| e.to_string())?;
    let snap_value: serde_json::Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    let snapshot_id = snap_value
        .get("snapshot_id")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    if snap_value.get("schema_version").and_then(|v| v.as_u64()) == Some(2) {
        let parent = snap_value
            .get("parent_lineage_digest_hex")
            .and_then(|v| v.as_str())
            .unwrap_or_default();
        if parent != replay.lineage_digest_hex {
            if let Some(dir) = state_dir {
                quarantine_state(dir, "snapshot lineage mismatch")?;
            }
            let mut ctx = ReplayContext::from_replay(&replay, &journal_digest);
            ctx.log_path = Some(log_path.to_string());
            ctx.ledger.set_snapshot_id(snapshot_id.clone());
            fs::write(log_path, "").map_err(|e| e.to_string())?;
            return Ok(RecoveryOutcome {
                ledger: ForgeLedger::new(),
                rollback: true,
                rollback_reason: Some("snapshot_lineage_mismatch".into()),
                snapshot_id,
                warnings: replay.warnings.clone(),
                ctx,
            });
        }
    }
    let (baseline, snap_id) = ForgeLedger::load_from_file(snapshot_path)?;
    let snapshot_id = snapshot_id.or(snap_id);
    let backup = baseline.snapshot();
    let temp_log = format!("{log_path}.tmp");

    let mut ctx = ReplayContext::with_ledger(
        baseline.clone_state(),
        die_root.to_string(),
        &replay.scenario_tag,
    );
    ctx.ledger
        .set_digest_context(&journal_digest, die_root, &lineage_digest_hex);
    ctx.ledger.set_snapshot_id(snapshot_id.clone());
    ctx.current_epoch = ctx.ledger.forge_epoch();
    ctx.log_path = Some(temp_log.clone());
    ctx.warnings.extend(replay.warnings.clone());
    for tomb in &replay.tombstone_audit {
        ctx.emit_tombstone_audit(tomb);
    }

    let mut rollback = false;
    let mut rollback_reason = None;
    for entry in &replay.entries {
        match ctx.try_apply_entry(entry) {
            Ok(()) => {}
            Err(err) => {
                ctx.warnings.push(err.clone());
                ctx.ledger = baseline.clone_state();
                ctx.ledger
                    .set_digest_context(&journal_digest, die_root, &lineage_digest_hex);
                ctx.ledger.set_snapshot_id(snapshot_id.clone());
                ctx.ledger.restore_snapshot(backup.clone());
                ctx.dies_sealed = 0;
                rollback = true;
                rollback_reason = Some("fdie failure".into());
                break;
            }
        }
    }

    if rollback {
        if Path::new(&temp_log).exists() {
            fs::remove_file(&temp_log).map_err(|e| e.to_string())?;
        }
        fs::write(log_path, "").map_err(|e| e.to_string())?;
        let mut rollback_entry = replay.entries.first().cloned().unwrap_or_else(|| {
            crate::journal::OpEntry {
                seq: 0,
                journal_revision: 1,
                op_id: "rollback".into(),
                op: "rollback".into(),
                scenario_tag: replay.scenario_tag.clone(),
                forge_epoch: 0,
                die_id: String::new(),
                shard_index: 0,
                source_path: String::new(),
                line_number: 0,
                ancestry_index: 0,
            }
        });
        rollback_entry.op = "recovery_rollback".into();
        ctx.log_path = Some(log_path.to_string());
        ctx.next_seq = 1;
        ctx.emit(
            "recovery_rollback",
            &rollback_entry,
            BTreeMap::from([(
                "reason".into(),
                serde_json::json!(rollback_reason.clone().unwrap_or_default()),
            )]),
        );
    } else if Path::new(&temp_log).exists() {
        if Path::new(log_path).exists() {
            fs::remove_file(log_path).map_err(|e| e.to_string())?;
        }
        fs::rename(&temp_log, log_path).map_err(|e| e.to_string())?;
    }

    Ok(RecoveryOutcome {
        ledger: ctx.ledger.clone_state(),
        rollback,
        rollback_reason,
        snapshot_id,
        warnings: ctx.warnings.clone(),
        ctx,
    })
}

pub fn write_atomic(path: &str, body: &str) -> Result<(), String> {
    let tmp = format!("{path}.tmp");
    if let Some(parent) = Path::new(path).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    fs::write(&tmp, body).map_err(|e| e.to_string())?;
    fs::rename(&tmp, path).map_err(|e| e.to_string())
}
