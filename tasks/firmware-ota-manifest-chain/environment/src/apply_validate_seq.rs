use std::fs;

pub const SEQ_PATH: &str = "/app/state/ota/apply-validate-seq.json";

#[derive(serde::Serialize, serde::Deserialize)]
struct SeqFile {
    seq: u32,
}

pub fn read_seq() -> Result<u32, String> {
    if !std::path::Path::new(SEQ_PATH).exists() {
        return Ok(0);
    }
    let raw = fs::read_to_string(SEQ_PATH).map_err(|e| e.to_string())?;
    let parsed: SeqFile = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    Ok(parsed.seq)
}

pub fn bump_seq() -> Result<(), String> {
    let next = read_seq()? + 1;
    if let Some(parent) = std::path::Path::new(SEQ_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let body = serde_json::to_string(&SeqFile { seq: next }).map_err(|e| e.to_string())?;
    fs::write(SEQ_PATH, format!("{body}\n")).map_err(|e| e.to_string())
}
