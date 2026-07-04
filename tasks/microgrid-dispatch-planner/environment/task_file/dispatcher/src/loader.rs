use std::fs;
use std::path::Path;

use crate::types::{Config, Unit};

pub fn load_units(path: &Path) -> Vec<Unit> {
    let raw = fs::read_to_string(path).expect("cannot read units.jsonl");
    raw.lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str::<Unit>(l).expect("invalid unit json"))
        .collect()
}

pub fn load_config(path: &Path) -> Config {
    let raw = fs::read_to_string(path).expect("cannot read config.json");
    serde_json::from_str(&raw).expect("invalid config json")
}
