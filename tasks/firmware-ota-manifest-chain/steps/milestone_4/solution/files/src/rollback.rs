use std::fs;

use crate::rollback_staging::RollbackStaging;
use crate::session;
use crate::types::RollbackIndex;
use crate::util::{load_state, read, save_state, write_json};

fn validate_rollback(
    idx: &RollbackIndex,
    st: &crate::types::OtaState,
    current: u32,
) -> Result<u32, String> {
    let envelope = st
        .envelope
        .as_ref()
        .ok_or_else(|| "missing verified envelope from m1".to_string())?;
    if st.chunk_map_sha256.is_none() || st.chunk_binding_generation.is_none() {
        return Err("missing chunk map from m2".to_string());
    }
    if st.chunk_binding_generation != Some(st.workflow_generation) {
        return Err("stale chunk binding generation".to_string());
    }
    if idx.device != envelope.device {
        return Err("rollback device mismatch".to_string());
    }
    if idx.index < current {
        return Err("rollback index below current index".to_string());
    }
    Ok(idx.index)
}

pub fn run_validate(args: &[String]) -> Result<(), String> {
    if args.len() != 3 {
        return Err(
            "usage: ota-chain m3-validate <rollback.json> <state.json> <current-index.txt>"
                .to_string(),
        );
    }
    let idx: RollbackIndex =
        serde_json::from_slice(&read(&args[0])?).map_err(|e| e.to_string())?;
    let st = load_state(&args[1]);
    let current = fs::read_to_string(&args[2])
        .map_err(|e| e.to_string())?
        .trim()
        .parse::<u32>()
        .map_err(|e| e.to_string())?;
    let accepted = validate_rollback(&idx, &st, current)?;
    let staging = RollbackStaging {
        device: idx.device.clone(),
        index: accepted,
        current_index: current,
        workflow_generation: st.workflow_generation,
    };
    crate::rollback_staging::write_staging(&staging)
}

pub fn run_commit(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err("usage: ota-chain m3-commit <state.json> <out.json>".to_string());
    }
    let epoch_before = session::capture_epoch()?;
    let staging = crate::rollback_staging::load_staging()?;
    let mut st = load_state(&args[0]);
    if staging.workflow_generation != st.workflow_generation {
        return Err("stale rollback staging generation".to_string());
    }
    st.rollback_index = Some(staging.index);
    save_state(&args[0], &st)?;
    write_json(
        &args[1],
        &serde_json::json!({"rollback_ok": true, "index": staging.index}),
    )?;
    session::assert_epoch_unchanged(&epoch_before)
}

pub fn run(args: &[String]) -> Result<(), String> {
    if args.len() != 4 {
        return Err(
            "usage: ota-chain m3 <rollback.json> <state.json> <current-index.txt> <out.json>"
                .to_string(),
        );
    }
    run_validate(&[args[0].clone(), args[1].clone(), args[2].clone()])?;
    run_commit(&[args[1].clone(), args[3].clone()])
}
