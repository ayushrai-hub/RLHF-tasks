use std::fs::{self, OpenOptions};
use std::io::Write;

const JOURNAL_PATH: &str = "/app/state/ota/apply-journal.jsonl";

pub fn clear_journal() -> Result<(), String> {
    if let Some(parent) = std::path::Path::new(JOURNAL_PATH).parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    fs::write(JOURNAL_PATH, b"").map_err(|e| e.to_string())
}

pub fn append_run(run_id: &str, generation: u32) -> Result<(), String> {
    let line = serde_json::json!({"run_id": run_id, "generation": generation});
    let mut row = serde_json::to_string(&line).map_err(|e| e.to_string())?;
    row.push('\n');
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(JOURNAL_PATH)
        .map_err(|e| e.to_string())?;
    file.write_all(row.as_bytes())
        .map_err(|e| e.to_string())
}

pub fn read_lines() -> Result<Vec<String>, String> {
    let raw = fs::read_to_string(JOURNAL_PATH).unwrap_or_default();
    Ok(raw.lines().filter(|l| !l.trim().is_empty()).map(str::to_string).collect())
}
