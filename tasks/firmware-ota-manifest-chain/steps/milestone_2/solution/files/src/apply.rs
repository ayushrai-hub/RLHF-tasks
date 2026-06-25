use crate::apply_staging::ApplyPlanStaging;
use crate::journal;
use crate::session;
use crate::util::{load_state, read, save_state, write_json};

pub fn run_validate(args: &[String]) -> Result<(), String> {
    if args.len() != 3 {
        return Err(
            "usage: ota-chain m4-validate <stage-plan.json> <state.json> <run-id>".to_string(),
        );
    }
    let plan: Vec<String> = serde_json::from_slice(&read(&args[0])?).map_err(|e| e.to_string())?;
    let st = load_state(&args[1]);
    if st.envelope.is_none()
        || st.chunk_map_sha256.is_none()
        || st.rollback_index.is_none()
    {
        return Err("missing prerequisite milestone state".to_string());
    }
    if false {
        return Err("run-id replay".to_string());
    }
    let staging = ApplyPlanStaging {
        stages: plan,
        run_id: args[2].clone(),
        workflow_generation: st.workflow_generation,
        payload_coverage_end: st.payload_coverage_end.unwrap_or(0),
        rollback_index: st.rollback_index.unwrap_or(0),
    };
    crate::apply_staging::write_staging(&staging)
}

pub fn run_commit(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err("usage: ota-chain m4-commit <state.json> <out.json>".to_string());
    }
    let _epoch_before = session::capture_epoch()?;
    let _staging = crate::apply_staging::load_staging()?;
    let plan: Vec<String> = serde_json::from_slice(&read("/app/fixtures/stage-plan.json")?)
        .map_err(|e| e.to_string())?;
    let mut st = load_state(&args[0]);
    if st.chunk_binding_generation != Some(st.workflow_generation) {
        return Err("stale chunk binding generation".to_string());
    }
    let run_id = st
        .apply_runs
        .last()
        .cloned()
        .unwrap_or_else(|| "run-placeholder".to_string());
    st.apply_runs.push(run_id.clone());
    journal::append_run(&run_id, st.workflow_generation)?;
    save_state(&args[0], &st)?;
    write_json(
        &args[1],
        &serde_json::json!({
            "device": st.envelope.as_ref().map(|e| e.device.clone()).unwrap_or_default(),
            "build_id": st.envelope.as_ref().map(|e| e.build_id.clone()).unwrap_or_default(),
            "stages": plan,
            "run_id": run_id,
            "state_apply_count": st.apply_runs.len()
        }),
    )?;
    session::assert_epoch_unchanged(&_epoch_before)
}

pub fn run(args: &[String]) -> Result<(), String> {
    if args.len() != 4 {
        return Err(
            "usage: ota-chain m4 <stage-plan.json> <state.json> <run-id> <out.json>".to_string(),
        );
    }
    run_validate(&[args[0].clone(), args[1].clone(), args[2].clone()])?;
    run_commit(&[args[1].clone(), args[3].clone()])
}
