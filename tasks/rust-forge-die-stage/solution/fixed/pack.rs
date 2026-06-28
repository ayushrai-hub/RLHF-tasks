use serde::Deserialize;
use std::fs;
use std::path::{Component, Path, PathBuf};

#[derive(Debug, Clone, Deserialize)]
pub struct ShardRef {
    pub id: u64,
    pub path: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct JournalPack {
    pub scenario_tag: String,
    pub pack_generation: u64,
    pub journal_revision: u64,
    pub shards: Vec<ShardRef>,
}

pub fn is_pack_dir(path: &str) -> bool {
    let p = Path::new(path);
    p.is_dir() && p.join("manifest.json").is_file()
}

pub fn load_pack(path: &str) -> Result<(JournalPack, PathBuf), String> {
    let pack_dir = PathBuf::from(path);
    let manifest_path = pack_dir.join("manifest.json");
    let raw = fs::read_to_string(&manifest_path).map_err(|e| e.to_string())?;
    let pack: JournalPack = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    Ok((pack, pack_dir))
}

pub fn resolve_shard_path(pack_dir: &Path, shard_path: &str) -> Result<PathBuf, String> {
    let joined = pack_dir.join(shard_path);
    let canonical_pack = pack_dir
        .canonicalize()
        .map_err(|e| format!("pack directory unreadable: {e}"))?;
    let canonical_shard = joined
        .canonicalize()
        .map_err(|e| format!("shard path escapes pack directory: {e}"))?;
    if !canonical_shard.starts_with(&canonical_pack) {
        return Err(format!("shard path escapes pack directory: {shard_path}"));
    }
  for component in Path::new(shard_path).components() {
        if matches!(component, Component::ParentDir) {
            return Err(format!("shard path escapes pack directory: {shard_path}"));
        }
    }
    Ok(joined)
}

pub fn manifest_path_for(input_path: &str) -> Option<String> {
    if is_pack_dir(input_path) {
        Some(
            Path::new(input_path)
                .join("manifest.json")
                .to_string_lossy()
                .to_string(),
        )
    } else {
        None
    }
}
