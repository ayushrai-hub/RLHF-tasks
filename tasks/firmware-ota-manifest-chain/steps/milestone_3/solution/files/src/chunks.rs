use crate::chunk_digest;
use crate::chunk_staging::ChunkMapStaging;
use crate::journal;
use crate::session;
use crate::types::DeltaChunk;
use crate::util::{load_state, read, save_state, sha256_hex, write_json};

fn validate_chunks(
    chunks: &[DeltaChunk],
    payload: &[u8],
    envelope_payload_sha256: &str,
) -> Result<(String, u32), String> {
    if sha256_hex(payload) != envelope_payload_sha256 {
        return Err("payload digest mismatch with envelope".to_string());
    }
    let mut last_end = 0u32;
    for ch in chunks {
        if ch.start != last_end {
            return Err("chunk coverage gap or overlap".to_string());
        }
        if ch.end <= ch.start || ch.end as usize > payload.len() {
            return Err("chunk byte bounds invalid".to_string());
        }
        let seg = &payload[ch.start as usize..ch.end as usize];
        if sha256_hex(seg) != ch.sha256 {
            return Err(format!("chunk sha256 mismatch: {}", ch.id));
        }
        last_end = ch.end;
    }
    Ok((chunk_digest::digest_chunk_map(chunks), last_end))
}

pub fn run_validate(args: &[String]) -> Result<(), String> {
    if args.len() != 3 {
        return Err(
            "usage: ota-chain m2-validate <chunks.json> <state.json> <payload.bin>".to_string(),
        );
    }
    let chunks: Vec<DeltaChunk> =
        serde_json::from_slice(&read(&args[0])?).map_err(|e| e.to_string())?;
    let st = load_state(&args[1]);
    let envelope = st
        .envelope
        .as_ref()
        .ok_or_else(|| "missing verified envelope from m1".to_string())?;
    let payload = read(&args[2])?;
    let (digest, last_end) = validate_chunks(&chunks, &payload, &envelope.payload_sha256)?;
    let staging = ChunkMapStaging {
        chunk_map_sha256: digest,
        chunks_verified: chunks.len(),
        payload_coverage_end: last_end,
        payload_sha256: envelope.payload_sha256.clone(),
        workflow_generation: st.workflow_generation,
    };
    crate::chunk_staging::write_staging(&staging)
}

pub fn run_commit(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err("usage: ota-chain m2-commit <state.json> <out.json>".to_string());
    }
    let epoch_before = session::capture_epoch()?;
    let staging = crate::chunk_staging::load_staging()?;
    let mut st = load_state(&args[0]);
    let envelope = st
        .envelope
        .as_ref()
        .ok_or_else(|| "missing verified envelope from m1".to_string())?;
    if staging.workflow_generation != st.workflow_generation {
        return Err("stale chunk map staging generation".to_string());
    }
    if staging.payload_sha256 != envelope.payload_sha256 {
        return Err("payload digest mismatch with envelope".to_string());
    }
    st.chunk_map_sha256 = Some(staging.chunk_map_sha256);
    st.payload_coverage_end = Some(staging.payload_coverage_end);
    st.chunk_binding_generation = Some(st.workflow_generation);
    st.rollback_index = None;
    st.apply_runs.clear();
    journal::clear_journal()?;
    save_state(&args[0], &st)?;
    write_json(
        &args[1],
        &serde_json::json!({
            "chunks_verified": staging.chunks_verified,
            "last_end": staging.payload_coverage_end
        }),
    )?;
    session::assert_epoch_unchanged(&epoch_before)
}

pub fn run(args: &[String]) -> Result<(), String> {
    if args.len() != 4 {
        return Err(
            "usage: ota-chain m2 <chunks.json> <state.json> <payload.bin> <out.json>".to_string(),
        );
    }
    run_validate(&[args[0].clone(), args[1].clone(), args[2].clone()])?;
    run_commit(&[args[1].clone(), args[3].clone()])
}
