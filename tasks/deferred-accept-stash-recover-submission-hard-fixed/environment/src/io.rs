use std::fs;
use std::path::Path;

use crate::errors::GateError;
use crate::model::Root;

pub fn ensure_state(root: &Root) -> Result<(), GateError> {
    fs::create_dir_all(root.state_dir()).map_err(|e| GateError::new(2, e.to_string()))
}

pub fn read_seed_rows(root: &Root) -> Result<Vec<(String, String, u32)>, GateError> {
    let text = fs::read_to_string(root.seed_file()).map_err(|e| GateError::new(3, e.to_string()))?;
    let mut out = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let parts: Vec<&str> = line.split('|').collect();
        if parts.len() != 3 {
            continue;
        }
        let weight: u32 = parts[2].parse().unwrap_or(0);
        out.push((parts[0].to_string(), parts[1].to_string(), weight));
    }
    Ok(out)
}

pub fn append_jsonl(path: &Path, lines: &[String]) -> Result<(), GateError> {
    if lines.is_empty() {
        return Ok(());
    }
    let mut body = String::new();
    for line in lines {
        body.push_str(line);
        body.push('\n');
    }
    if path.exists() {
        let prior = fs::read_to_string(path).unwrap_or_default();
        body = format!("{prior}{body}");
    }
    fs::write(path, body).map_err(|e| GateError::new(4, e.to_string()))
}

pub fn write_jsonl(path: &Path, lines: &[String]) -> Result<(), GateError> {
    append_jsonl(path, lines)
}

pub fn write_json(path: &Path, body: &str) -> Result<(), GateError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| GateError::new(5, e.to_string()))?;
    }
    fs::write(path, body).map_err(|e| GateError::new(6, e.to_string()))
}

pub fn read_json(path: &Path) -> Result<String, GateError> {
    fs::read_to_string(path).map_err(|e| GateError::new(7, e.to_string()))
}
