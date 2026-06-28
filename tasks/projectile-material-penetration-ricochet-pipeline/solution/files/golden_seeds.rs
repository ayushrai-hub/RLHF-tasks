use std::fs;
use std::path::Path;

use serde::Deserialize;

use crate::model::Vec3;

#[derive(Debug, Deserialize)]
struct SeedEntry {
    seed: u64,
    velocity_scale: f64,
}

#[derive(Debug, Deserialize)]
struct SeedsFile {
    seeds: Vec<SeedEntry>,
}

pub fn apply_seed_scale(seeds_path: &Path, seed: u64, velocity: &mut Vec3) {
    let Ok(raw) = fs::read_to_string(seeds_path) else {
        return;
    };
    let Ok(body) = serde_json::from_str::<SeedsFile>(&raw) else {
        return;
    };
    let Some(entry) = body.seeds.iter().find(|s| s.seed == seed) else {
        return;
    };
    let mag = velocity.magnitude();
    if mag > 0.0 {
        *velocity = velocity.scale(entry.velocity_scale);
    }
}
