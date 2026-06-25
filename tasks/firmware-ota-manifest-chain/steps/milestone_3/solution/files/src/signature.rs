use std::collections::BTreeMap;

use crate::envelope_staging::VerifiedEnvelopeStaging;
use crate::journal;
use crate::session;
use crate::sig_canon;
use crate::types::Envelope;
use crate::util::{load_state, read, save_state, sha256_hex, write_json};

pub fn verify_sig(env: &Envelope, key: &str) -> String {
    sha256_hex(sig_canon::canonical_sig_input(env, key).as_bytes())
}

fn verify_envelope(envelope_path: &str, keys_path: &str) -> Result<Envelope, String> {
    let env: Envelope = serde_json::from_slice(&read(envelope_path)?).map_err(|e| e.to_string())?;
    let keys: BTreeMap<String, String> =
        serde_json::from_slice(&read(keys_path)?).map_err(|e| e.to_string())?;
    let epoch_key = keys
        .get(&env.epoch.to_string())
        .ok_or_else(|| "unknown epoch key".to_string())?;
    let expected = verify_sig(&env, epoch_key);
    if expected != env.sig {
        return Err("envelope signature mismatch".to_string());
    }
    Ok(env)
}

pub fn run_verify(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err(
            "usage: ota-chain m1-verify <envelope.json> <epoch-keys.json>".to_string(),
        );
    }
    let env = verify_envelope(&args[0], &args[1])?;
    let staging = VerifiedEnvelopeStaging {
        device: env.device.clone(),
        epoch: env.epoch,
        envelope: env,
        verified: true,
    };
    crate::envelope_staging::write_staging(&staging)
}

pub fn run_commit(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err("usage: ota-chain m1-commit <state.json> <out.json>".to_string());
    }
    let epoch_before = session::capture_epoch()?;
    let staging = crate::envelope_staging::load_staging()?;
    let mut st = load_state(&args[0]);
    st.envelope = Some(staging.envelope.clone());
    st.workflow_generation = st.workflow_generation.saturating_add(1);
    st.chunk_map_sha256 = None;
    st.payload_coverage_end = None;
    st.chunk_binding_generation = None;
    st.rollback_index = None;
    st.apply_runs.clear();
    journal::clear_journal()?;
    save_state(&args[0], &st)?;
    write_json(
        &args[1],
        &serde_json::json!({"verified": true, "device": staging.device, "epoch": staging.epoch}),
    )?;
    session::assert_epoch_unchanged(&epoch_before)
}

pub fn run(args: &[String]) -> Result<(), String> {
    if args.len() != 4 {
        return Err(
            "usage: ota-chain m1 <envelope.json> <epoch-keys.json> <state.json> <out.json>"
                .to_string(),
        );
    }
    run_verify(&[args[0].clone(), args[1].clone()])?;
    run_commit(&[args[2].clone(), args[3].clone()])
}
