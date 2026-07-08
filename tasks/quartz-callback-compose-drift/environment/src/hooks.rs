use crate::types::{FireEffect, HookDef};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

pub fn load_hooks(path: &Path) -> std::io::Result<HashMap<String, HookDef>> {
    let text = fs::read_to_string(path)?;
    let mut lines = text.lines();
    let _ = lines.next();
    let mut hooks = HashMap::new();
    for line in lines {
        if line.trim().is_empty() {
            continue;
        }
        let c: Vec<_> = line.split('|').collect();
        let on_fire = match c[2].trim() {
            "none" => None,
            s if s.starts_with("add:") => Some(FireEffect::Add(s[4..].parse().unwrap_or(0.0))),
            s if s.starts_with("mul:") => Some(FireEffect::Mul(s[4..].parse().unwrap_or(1.0))),
            s if s.starts_with("set:") => Some(FireEffect::Set(s[4..].parse().unwrap_or(0.0))),
            _ => None,
        };
        let name: String = c[0].into();
        hooks.insert(
            name.clone(),
            HookDef {
                name,
                threshold: c[1].parse().unwrap_or(0.0),
                on_fire,
            },
        );
    }
    Ok(hooks)
}
