use std::fs;
use std::path::{Path, PathBuf};

pub fn sessions_root() -> PathBuf {
    if let Ok(override_path) = std::env::var("NEF_SESSIONS_ROOT") {
        if !override_path.is_empty() {
            return PathBuf::from(override_path);
        }
    }
    PathBuf::from("/app/data/sessions")
}

pub fn policy_path() -> Result<PathBuf, String> {
    if let Ok(override_path) = std::env::var("NEF_POLICY_PATH") {
        if !override_path.is_empty() {
            let path = PathBuf::from(&override_path);
            if !path.is_absolute() {
                return Err("NEF_POLICY_PATH must be absolute".into());
            }
            return Ok(path);
        }
    }
    Ok(PathBuf::from("/app/data/policies/memory-policy.json"))
}

pub fn discover_session_shards(root: &Path) -> Result<Vec<PathBuf>, String> {
    let order_path = root.join("load-order.json");
    let names: Vec<String> = if order_path.is_file() {
        serde_json::from_str(&fs::read_to_string(&order_path).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?
    } else {
        let mut names: Vec<String> = fs::read_dir(root)
            .map_err(|e| e.to_string())?
            .filter_map(|e| e.ok())
            .map(|e| e.file_name().to_string_lossy().into_owned())
            .filter(|n| n.ends_with(".jsonl"))
            .collect();
        names.sort();
        names
    };
    let mut paths = Vec::new();
    for name in names {
        let candidate = root.join(&name);
        if candidate.is_file() {
            paths.push(candidate);
        }
    }
    Ok(paths)
}
