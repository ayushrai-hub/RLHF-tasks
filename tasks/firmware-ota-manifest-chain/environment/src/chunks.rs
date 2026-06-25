use crate::chunk_digest;
use crate::chunk_staging::ChunkMapStaging;
use crate::journal;
use crate::session;
use crate::types::DeltaChunk;
use crate::util::{load_state, read, save_state, sha256_hex, write_json};

fn validate_chunks(chunks: &[DeltaChunk], payload: &[u8]) -> Result<u32, String> {
    let mut last_end = 0u32;
    for ch in chunks {
        if ch.start <= last_end {
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
    Ok(last_end)
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
    if st.envelope.is_none() {
        return Err("missing verified envelope from m1".to_string());
    }
    let payload = read(&args[2])?;
    let last_end = validate_chunks(&chunks, &payload)?;
    let staging = ChunkMapStaging {
        chunk_map_sha256: chunk_digest::digest_chunk_map(&chunks),
        chunks_verified: chunks.len(),
        payload_coverage_end: last_end,
        payload_sha256: st
            .envelope
            .as_ref()
            .map(|e| e.payload_sha256.clone())
            .unwrap_or_default(),
        workflow_generation: st.workflow_generation,
    };
    crate::chunk_staging::write_staging(&staging)
}

pub fn run_commit(args: &[String]) -> Result<(), String> {
    if args.len() != 2 {
        return Err("usage: ota-chain m2-commit <state.json> <out.json>".to_string());
    }
    let _epoch_before = session::capture_epoch()?;
    let _staging = crate::chunk_staging::load_staging()?;
    let chunks: Vec<DeltaChunk> = serde_json::from_slice(&read("/app/fixtures/chunks.json")?)
        .map_err(|e| e.to_string())?;
    let mut st = load_state(&args[0]);
    let payload = read("/app/fixtures/payload.bin")?;
    let last_end = validate_chunks(&chunks, &payload)?;
    st.chunk_map_sha256 = Some(chunk_digest::digest_chunk_map(&chunks));
    save_state(&args[0], &st)?;
    write_json(
        &args[1],
        &serde_json::json!({"chunks_verified": chunks.len(), "last_end": last_end}),
    )?;
    journal::clear_journal()
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
