use crate::state::PrincipalRec;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

pub fn load_tree(path: &Path) -> HashMap<String, PrincipalRec> {
    let mut slots = HashMap::new();
    let text = fs::read_to_string(path).unwrap_or_default();
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let mut name = String::new();
        let mut principal = String::new();
        let mut label = String::new();
        let mut gen = 0u32;
        let mut action_code = 0i32;
        for item in line.split_whitespace() {
            if let Some((k, v)) = item.split_once('=') {
                match k {
                    "ward" | "spool" => name = v.to_string(),
                    "principal" => principal = v.to_string(),
                    "label" => label = v.to_string(),
                    "gen" => gen = v.parse().unwrap_or(0),
                    "action" => action_code = v.parse().unwrap_or(0),
                    _ => {}
                }
            }
        }
        if !name.is_empty() {
            slots.insert(
                name,
                PrincipalRec {
                    principal,
                    label,
                    gen,
                    action_code,
                },
            );
        }
    }
    slots
}

pub fn load_frag(path: &Path) -> (u32, String) {
    let text = fs::read_to_string(path).unwrap_or_default();
    let mut epoch = 1u32;
    let mut digest = String::new();
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        for item in line.split_whitespace() {
            if let Some((k, v)) = item.split_once('=') {
                match k {
                    "epoch" => epoch = v.parse().unwrap_or(1),
                    "digest" => digest = v.to_string(),
                    _ => {}
                }
            }
        }
    }
    (epoch, digest)
}

pub fn active_slot(slots: &HashMap<String, PrincipalRec>) -> Option<PrincipalRec> {
    slots.get("active").cloned()
}
