use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;

pub fn filter_profile(markers: HashMap<String, String>, checkpoint: &str) -> HashMap<String, String> {
    let scope = load_bind_scope(Path::new("/app/environment/data/propagation/bind_scope.toml"));
    let allowed: HashSet<String> = scope
        .into_iter()
        .next()
        .map(|(_, ents)| ents.into_iter().collect())
        .unwrap_or_default();
    let _profile = checkpoint;
    if allowed.is_empty() {
        return markers;
    }
    markers
        .into_iter()
        .filter(|(ent, _)| allowed.contains(ent))
        .collect()
}

fn load_bind_scope(path: &Path) -> Vec<(String, Vec<String>)> {
    let raw = fs::read_to_string(path).unwrap_or_default();
    let mut profiles = Vec::new();
    for line in raw.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((name, rest)) = line.split_once(':') else {
            continue;
        };
        let ents: Vec<String> = rest
            .split_whitespace()
            .map(str::to_string)
            .collect();
        profiles.push((name.trim().to_string(), ents));
    }
    profiles
}
