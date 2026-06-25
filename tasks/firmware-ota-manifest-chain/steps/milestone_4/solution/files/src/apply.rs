use crate::apply_staging::{compute_plan_digest, ApplyPlanStaging};
use crate::apply_validate_seq;
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
        || st.payload_coverage_end.is_none()
        || st.rollback_index.is_none()
        || st.chunk_binding_generation.is_none()
    {
        return Err("missing prerequisite milestone state".to_string());
    }
    if st.chunk_binding_generation != Some(st.workflow_generation) {
        return Err("stale chunk binding generation".to_string());
    }
    let coverage = st.payload_coverage_end.unwrap();
    let rollback = st.rollback_index.unwrap();
    if rollback < coverage {
        return Err("rollback index below payload coverage".to_string());
    }
    if st.apply_runs.iter().any(|r| r == &args[2]) {
        return Err("run-id replay".to_string());
    }
    let validate_seq = apply_validate_seq::read_seq()?;
    let plan_digest = compute_plan_digest(&plan);
    let staging = ApplyPlanStaging {
        stages: plan,
        run_id: args[2].clone(),
        workflow_generation: st.workflow_generation,
        payload_coverage_end: coverage,
        rollback_index: rollback,
        plan_digest,
        validate_seq,
    };
    crate::apply_staging::write_staging(&staging)?;
    apply_validate_seq::bump_seq()
}

pub fn run_commit(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err("usage: ota-chain m4-commit <state.json> <out.json>".to_string());
    }
    let epoch_before = session::capture_epoch()?;
    let staging = crate::apply_staging::load_staging()?;
    let current_seq = apply_validate_seq::read_seq()?;
    if current_seq != staging.validate_seq + 1 {
        return Err("stale apply validate sequence".to_string());
    }
    if staging.plan_digest != compute_plan_digest(&staging.stages) {
        return Err("apply plan digest mismatch".to_string());
    }
    let mut st = load_state(&args[0]);
    if staging.workflow_generation != st.workflow_generation {
        return Err("stale apply plan staging generation".to_string());
    }
    if staging.rollback_index < staging.payload_coverage_end {
        return Err("rollback index below payload coverage".to_string());
    }
    if st.apply_runs.iter().any(|r| r == &staging.run_id) {
        return Err("run-id replay".to_string());
    }
    st.apply_runs.push(staging.run_id.clone());
    journal::append_run(&staging.run_id, st.workflow_generation)?;
    save_state(&args[0], &st)?;
    write_json(
        &args[1],
        &serde_json::json!({
            "device": st.envelope.as_ref().map(|e| e.device.clone()).unwrap_or_default(),
            "build_id": st.envelope.as_ref().map(|e| e.build_id.clone()).unwrap_or_default(),
            "stages": staging.stages,
            "run_id": staging.run_id,
            "state_apply_count": st.apply_runs.len()
        }),
    )?;
    session::assert_epoch_unchanged(&epoch_before)
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
