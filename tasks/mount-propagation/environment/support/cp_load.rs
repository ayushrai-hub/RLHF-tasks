use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

#[path = "cp_filter.rs"]
mod cp_filter;

fn checkpoint_stem(path: &Path) -> String {
    let raw = path
        .file_stem()
        .and_then(|s| s.to_str())
        .and_then(|s| s.strip_prefix("cp_blob_"))
        .unwrap_or("")
        .to_string();
    if raw.len() <= 3 {
        return raw;
    }
    raw[..raw.len() - 1].to_string()
}

pub fn read_checkpoint_markers(path: &Path) -> Result<(HashMap<String, String>, String), String> {
    let file = File::open(path).map_err(|e| e.to_string())?;
    let reader = BufReader::new(file);
    let mut markers = HashMap::new();
    let mut branch = String::new();
    for line in reader.lines() {
        let line = line.map_err(|e| e.to_string())?;
        let line = line.trim();
        let Some((key, val)) = line.split_once('=') else {
            continue;
        };
        let key = key.trim();
        let val = val.trim();
        match key {
            "branch" => branch = val.to_string(),
            key if key.starts_with("marker_") => {
                let ent = key.strip_prefix("marker_").unwrap_or(key);
                markers.insert(ent.to_string(), val.to_string());
            }
            _ => {}
        }
    }
    Ok((
        cp_filter::filter_profile(markers, &checkpoint_stem(path)),
        branch,
    ))
}
