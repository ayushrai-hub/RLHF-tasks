use crate::pack::{load_pack, JournalPack};
use serde::Deserialize;
use std::collections::HashMap;
use std::path::{Component, Path, PathBuf};

#[derive(Debug, Clone, Deserialize)]
pub struct BundlePackRef {
    pub id: String,
    pub path: String,
    pub parent: Option<String>,
    pub generation: u64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct JournalBundle {
    pub bundle_schema: u64,
    pub scenario_tag: String,
    pub root_pack: String,
    pub packs: Vec<BundlePackRef>,
}

#[derive(Debug, Clone)]
pub struct OrderedPack {
    pub id: String,
    pub pack: JournalPack,
    pub pack_dir: PathBuf,
    pub ancestry_index: usize,
    pub generation: u64,
}

pub fn is_bundle_dir(path: &str) -> bool {
    let p = Path::new(path);
    p.is_dir() && p.join("bundle.json").is_file()
}

pub fn load_bundle(path: &str) -> Result<(JournalBundle, PathBuf, Vec<OrderedPack>), String> {
    let bundle_dir = PathBuf::from(path);
    let raw = std::fs::read_to_string(bundle_dir.join("bundle.json")).map_err(|e| e.to_string())?;
    let bundle: JournalBundle = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    if bundle.bundle_schema != 2 {
        return Err("unsupported bundle schema".into());
    }
    let by_id: HashMap<String, &BundlePackRef> = bundle.packs.iter().map(|p| (p.id.clone(), p)).collect();
    if !by_id.contains_key(&bundle.root_pack) {
        return Err("root_pack missing from bundle".into());
    }
    let mut children: HashMap<String, String> = HashMap::new();
    for pack in &bundle.packs {
        if let Some(parent) = &pack.parent {
            if children.insert(parent.clone(), pack.id.clone()).is_some() {
                return Err("bundle parent chain is not linear".into());
            }
            if !by_id.contains_key(parent) {
                return Err(format!("unknown parent pack: {parent}"));
            }
        }
        let joined = bundle_dir.join(&pack.path);
        let canonical_bundle = bundle_dir
            .canonicalize()
            .map_err(|e| format!("bundle directory unreadable: {e}"))?;
        let canonical_pack = joined
            .canonicalize()
            .map_err(|e| format!("pack path escapes bundle: {e}"))?;
        if !canonical_pack.starts_with(&canonical_bundle) {
            return Err(format!("pack path escapes bundle: {}", pack.path));
        }
        for component in Path::new(&pack.path).components() {
            if matches!(component, Component::ParentDir) {
                return Err(format!("pack path escapes bundle: {}", pack.path));
            }
        }
    }
    let mut ordered_ids = vec![bundle.root_pack.clone()];
    while let Some(child) = children.get(ordered_ids.last().unwrap()).cloned() {
        ordered_ids.push(child);
    }
    if ordered_ids.len() != bundle.packs.len() {
        return Err("bundle parent chain does not include all packs".into());
    }
    let mut ordered = Vec::new();
    for (ancestry_index, pack_id) in ordered_ids.iter().enumerate() {
        let pack_ref = by_id
            .get(pack_id)
            .ok_or_else(|| format!("missing pack {pack_id}"))?;
        let pack_path = bundle_dir.join(&pack_ref.path);
        let (pack, pack_dir) = load_pack(pack_path.to_str().unwrap_or_default())?;
        ordered.push(OrderedPack {
            id: pack_ref.id.clone(),
            pack,
            pack_dir,
            ancestry_index,
            generation: pack_ref.generation,
        });
    }
    Ok((bundle, bundle_dir, ordered))
}
