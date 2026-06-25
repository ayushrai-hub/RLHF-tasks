#!/usr/bin/env bash
set -euo pipefail

cd /app/environment

cat > /app/m3l/src/trim.rs <<'EOF'
use crate::pool::Engine;

pub fn apply(engine: &mut Engine, ceiling: u32) {
    engine.rows.retain(|r| r.seq <= ceiling);
    engine.applied = engine.rows.iter().filter(|r| r.digest_ok).count() as u32;
}

pub fn apply_floor_cut(engine: &mut Engine, floor: u32) {
    engine.rows.retain(|r| r.seq >= floor);
    engine.applied = engine.rows.iter().filter(|r| r.digest_ok).count() as u32;
}

pub fn apply_modulo_prune(engine: &mut Engine, modulo: u32) {
    engine.rows.retain(|r| r.seq % modulo != 0);
    engine.applied = engine.rows.iter().filter(|r| r.digest_ok).count() as u32;
}
EOF

cat > /app/m3l/src/profile.rs <<'EOF'
use crate::scan::ScenarioMeta;
use std::fs;
use std::path::PathBuf;

pub fn trim_sequence(meta: &ScenarioMeta) -> Vec<String> {
    if let Some(name) = &meta.profile {
        return load_profile(name);
    }
    default_sequence(meta)
}

fn default_sequence(meta: &ScenarioMeta) -> Vec<String> {
    if meta.rollback_after.is_some() {
        vec!["rollback_after".into()]
    } else if meta.prune_below.is_some() {
        vec!["prune_below".into()]
    } else {
        vec![]
    }
}

fn load_profile(name: &str) -> Vec<String> {
    let path = PathBuf::from("/app/profiles").join(format!("{name}.toml"));
    let raw = fs::read_to_string(path).unwrap_or_default();
    parse_trim_sequence(&raw)
}

fn parse_trim_sequence(raw: &str) -> Vec<String> {
    let Some(start) = raw.find('[') else {
        return vec![];
    };
    let Some(end) = raw[start..].find(']') else {
        return vec![];
    };
    raw[start + 1..start + end]
        .split(',')
        .map(|part| part.trim().trim_matches('"').to_string())
        .filter(|part| part == "rollback_after" || part == "prune_below")
        .collect()
}

fn parse_modulo_prune(raw: &str) -> Option<u32> {
    for line in raw.lines() {
        let parts: Vec<&str> = line.split('=').collect();
        if parts.len() == 2 && parts[0].trim() == "modulo_prune" {
            if let Ok(val) = parts[1].trim().parse::<u32>() {
                return Some(val);
            }
        }
    }
    None
}

pub fn apply_trim_steps(meta: &ScenarioMeta, engine: &mut crate::pool::Engine) {
    for step in trim_sequence(meta) {
        match step.as_str() {
            "rollback_after" => {
                if let Some(marker) = meta.rollback_after {
                    crate::trim::apply(engine, marker);
                }
            }
            "prune_below" => {
                if let Some(marker) = meta.prune_below {
                    crate::trim::apply_floor_cut(engine, marker);
                }
            }
            _ => {}
        }
    }
    if let Some(profile_name) = &meta.profile {
        let path = PathBuf::from("/app/profiles").join(format!("{profile_name}.toml"));
        let raw = fs::read_to_string(path).unwrap_or_default();
        if let Some(modulo) = parse_modulo_prune(&raw) {
            crate::trim::apply_modulo_prune(engine, modulo);
        }
    }
    if let Some(modulo) = meta.modulo_prune {
        crate::trim::apply_modulo_prune(engine, modulo);
    }
}
EOF

cat > /app/m3l/src/gate.rs <<'EOF'
use crate::cfg;
use crate::pool::Engine;
use crate::scan::ScenarioMeta;

pub fn apply_manifest_lane(engine: &mut Engine, meta: &ScenarioMeta) {
    if let Some(expect) = meta.plate_lane {
        engine.rows.retain(|r| r.plate_lane == expect);
    }
}

pub fn apply_profile_mask(engine: &mut Engine, profile: &cfg::Profile) {
    if profile.lane_mask == 0xFFFF {
        return;
    }
    engine.rows.retain(|r| ((profile.lane_mask >> r.plate_lane) & 1) == 1);
}
EOF

cat > /app/m3l/src/flow.rs <<'EOF'
use crate::cfg;
use crate::emit;
use crate::gate;
use crate::pool;
use crate::profile;
use crate::scan;
use std::path::PathBuf;

pub fn drive(args: impl Iterator<Item = String>) {
    let mut args = args;
    let _cmd = args.next().unwrap_or_default();
    let mut scenario = String::new();
    let mut output = PathBuf::new();
    while let Some(flag) = args.next() {
        match flag.as_str() {
            "--scenario" | "--pack" | "--bundle" | "--profile" | "--table"
    | "--checkpoint" | "--cache" | "--shard" | "--frame" | "--delta" | "--ring" | "--blob"
    | "--segment" | "--crate" | "--journal" | "--manifest" | "--index" | "--ledger" => {
                scenario = args.next().unwrap_or_default();
            }
            "--output" => output = PathBuf::from(args.next().unwrap_or_default()),
            _ => {}
        }
    }
    if scenario.is_empty() || output.as_os_str().is_empty() {
        eprintln!("missing scenario or output");
        std::process::exit(2);
    }
    let meta_path = PathBuf::from("/app/fixtures/scenarios").join(format!("{scenario}.json"));
    let meta = scan::load_meta(&meta_path);
    let profile = meta
        .profile
        .as_deref()
        .map(cfg::load)
        .unwrap_or_else(cfg::default_profile);
    let seg_dir = PathBuf::from("/app/fixtures/segments").join(&scenario);
    let mut engine = pool::Engine::new(&seg_dir, &meta);
    gate::apply_manifest_lane(&mut engine, &meta);
    gate::apply_profile_mask(&mut engine, &profile);
    engine.rows.sort_by_key(|r| r.seq);
    engine.run();
    profile::apply_trim_steps(&meta, &mut engine);
    let cached = r8k::slot::read_head(&scenario, engine.applied);
    let rep = emit::build(&engine, &scenario, cached);
    emit::write_json(&output, &rep);
}
EOF

timeout 300 cargo build --release
/app/target/release/iodine-plate plate --ledger tab_trim --output /app/output/iodine_plate_report.json
