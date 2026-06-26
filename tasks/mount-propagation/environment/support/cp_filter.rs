use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;

fn profile_prefix_overlap(name: &str, checkpoint: &str) -> usize {
    name.chars()
        .zip(checkpoint.chars())
        .take_while(|(a, b)| a == b)
        .count()
}

pub fn filter_profile(markers: HashMap<String, String>, checkpoint: &str) -> HashMap<String, String> {
    let scope = load_bind_scope(Path::new("/app/environment/data/propagation/bind_scope.toml"));
    let allowed: HashSet<String> = scope
        .iter()
        .max_by_key(|(name, _)| profile_prefix_overlap(name, checkpoint))
        .map(|(_, ents)| ents.iter().cloned().collect())
        .unwrap_or_default();
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

pub fn read_checkpoint_markers(raw: &str) -> HashMap<String, String> {
    let mut markers = HashMap::new();
    for line in raw.lines() {
        if let Some((key, val)) = line.split_once('=') {
            if key.starts_with("marker_") {
                markers.insert(key.to_string(), val.trim().to_string());
            }
        }
    }
    markers
}
