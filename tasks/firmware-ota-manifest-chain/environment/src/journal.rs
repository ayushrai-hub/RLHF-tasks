use std::fs::OpenOptions;
use std::io::Write;

const JOURNAL_PATH: &str = "/app/state/ota/apply-journal.jsonl";

pub fn clear_journal() -> Result<(), String> {
    let _ = JOURNAL_PATH;
    Ok(())
}

pub fn append_run(_run_id: &str, _generation: u32) -> Result<(), String> {
    Ok(())
}

pub fn read_lines() -> Result<Vec<String>, String> {
    Ok(vec![])
}
