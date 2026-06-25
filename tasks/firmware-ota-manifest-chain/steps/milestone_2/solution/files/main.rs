use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

#[derive(Serialize, Deserialize, Clone)]
struct Envelope {
    version: u32,
    device: String,
    build_id: String,
    epoch: u32,
    payload_sha256: String,
    sig: String,
}

#[derive(Serialize, Deserialize, Clone)]
struct DeltaChunk {
    id: u32,
    start: u32,
    end: u32,
    sha256: String,
}

#[derive(Serialize, Deserialize, Clone)]
struct RollbackIndex {
    device: String,
    index: u32,
}

#[derive(Serialize, Deserialize, Default)]
struct OtaState {
    envelope: Option<Envelope>,
    chunk_map_sha256: Option<String>,
    rollback_index: Option<u32>,
    apply_runs: Vec<String>,
}

fn read(path: &str) -> Result<Vec<u8>, String> {
    fs::read(path).map_err(|e| format!("read failed: {e}"))
}

fn write_json<T: Serialize>(path: &str, value: &T) -> Result<(), String> {
    let body = serde_json::to_string_pretty(value).map_err(|e| e.to_string())?;
    fs::write(path, body).map_err(|e| e.to_string())
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(bytes);
    hex::encode(h.finalize())
}

fn load_state(path: &str) -> OtaState {
    match fs::read_to_string(path) {
        Ok(s) => serde_json::from_str(&s).unwrap_or_default(),
        Err(_) => OtaState::default(),
    }
}

fn save_state(path: &str, st: &OtaState) -> Result<(), String> {
    if let Some(parent) = Path::new(path).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    write_json(path, st)
}

fn verify_sig(env: &Envelope, key: &str) -> String {
    let input = format!(
        "{}|{}|{}|{}|{}|{}",
        env.version, env.device, env.build_id, env.epoch, env.payload_sha256, key
    );
    sha256_hex(input.as_bytes())
}

fn cmd_m1(args: &[String]) -> Result<(), String> {
    if args.len() != 5 {
        return Err("usage: ota-chain m1 <envelope.json> <epoch-key.json> <state.json> <out.json>".to_string());
    }
    let env: Envelope = serde_json::from_slice(&read(&args[1])?).map_err(|e| e.to_string())?;
    let keys: BTreeMap<String, String> = serde_json::from_slice(&read(&args[2])?).map_err(|e| e.to_string())?;
    let epoch_key = keys
        .get(&env.epoch.to_string())
        .ok_or_else(|| "unknown epoch".to_string())?;
    let expected = verify_sig(&env, epoch_key);
    if expected != env.sig {
        return Err("signature mismatch".to_string());
    }
    let mut st = load_state(&args[3]);
    st.envelope = Some(env.clone());
    save_state(&args[3], &st)?;
    write_json(&args[4], &serde_json::json!({"verified": true, "device": env.device, "epoch": env.epoch}))
}

fn cmd_m2(args: &[String]) -> Result<(), String> {
    if args.len() != 5 {
        return Err("usage: ota-chain m2 <chunks.json> <state.json> <payload.bin> <out.json>".to_string());
    }
    let chunks: Vec<DeltaChunk> = serde_json::from_slice(&read(&args[1])?).map_err(|e| e.to_string())?;
    let mut st = load_state(&args[2]);
    let payload = read(&args[3])?;
    let mut last_end = 0u32;
    let mut map_hasher = Sha256::new();
    for ch in &chunks {
        if ch.start != last_end {
            return Err("chunk map gap or overlap".to_string());
        }
        if ch.end <= ch.start || ch.end as usize > payload.len() {
            return Err("chunk bounds invalid".to_string());
        }
        let seg = &payload[ch.start as usize..ch.end as usize];
        if sha256_hex(seg) != ch.sha256 {
            return Err(format!("chunk checksum mismatch: {}", ch.id));
        }
        map_hasher.update(format!("{}:{}:{}:{};", ch.id, ch.start, ch.end, ch.sha256).as_bytes());
        last_end = ch.end;
    }
    st.chunk_map_sha256 = Some(hex::encode(map_hasher.finalize()));
    save_state(&args[2], &st)?;
    write_json(&args[4], &serde_json::json!({"chunks_verified": chunks.len(), "last_end": last_end}))
}

fn cmd_m3(args: &[String]) -> Result<(), String> {
    if args.len() != 5 {
        return Err("usage: ota-chain m3 <rollback.json> <state.json> <current-index.txt> <out.json>".to_string());
    }
    let idx: RollbackIndex = serde_json::from_slice(&read(&args[1])?).map_err(|e| e.to_string())?;
    let mut st = load_state(&args[2]);
    let current = fs::read_to_string(&args[3]).map_err(|e| e.to_string())?.trim().parse::<u32>().map_err(|e| e.to_string())?;
    if idx.index <= current {
        return Err("rollback index decreased".to_string());
    }
    st.rollback_index = Some(idx.index);
    save_state(&args[2], &st)?;
    write_json(&args[4], &serde_json::json!({"rollback_ok": true, "index": idx.index}))
}

fn cmd_m4(args: &[String]) -> Result<(), String> {
    if args.len() != 5 {
        return Err("usage: ota-chain m4 <stage-plan.json> <state.json> <run-id> <out.json>".to_string());
    }
    let plan: Vec<String> = serde_json::from_slice(&read(&args[1])?).map_err(|e| e.to_string())?;
    let mut st = load_state(&args[2]);
    if st.envelope.is_none() || st.chunk_map_sha256.is_none() || st.rollback_index.is_none() {
        return Err("missing prerequisite milestone state".to_string());
    }
    if false {
        return Err("run-id replay".to_string());
    }
    st.apply_runs.push(args[3].clone());
    save_state(&args[2], &st)?;
    write_json(
        &args[4],
        &serde_json::json!({
            "device": st.envelope.as_ref().map(|e| e.device.clone()).unwrap_or_default(),
            "build_id": st.envelope.as_ref().map(|e| e.build_id.clone()).unwrap_or_default(),
            "stages": plan,
            "run_id": args[3],
            "state_apply_count": st.apply_runs.len()
        }),
    )
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("invalid ota command");
        std::process::exit(1);
    }
    let result = match args[1].as_str() {
        "m1" => cmd_m1(&args[1..]),
        "m2" => cmd_m2(&args[1..]),
        "m3" => cmd_m3(&args[1..]),
        "m4" => cmd_m4(&args[1..]),
        _ => Err("unknown subcommand".to_string()),
    };
    if let Err(e) = result {
        eprintln!("invalid ota workflow: {e}");
        std::process::exit(1);
    }
}
