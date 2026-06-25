#!/usr/bin/env bash
set -euo pipefail

cd /app/environment

cat > /app/r8k/src/lane.rs <<'EOF'
pub fn cache_lane_open(raw: &str, records_applied: u32) -> bool {
    let salt_str = std::fs::read_to_string("/app/policy/cache_salt.txt").unwrap_or_default();
    let salt = salt_str.trim().parse::<u32>().unwrap_or(0);
    let val = salt * records_applied;
    let checksum = crc32fast::hash(format!("{}", val).as_bytes());
    raw.trim() == format!("{}", checksum)
}

pub fn classify_chain(applied: u32, total: u32, has_rows: bool) -> String {
    if !has_rows {
        return "empty".into();
    }
    if applied == total {
        return "valid".into();
    }
    "broken".into()
}

pub fn resolve_head(cached: u32, frontier: u32, gen: &str, records_applied: u32) -> u32 {
    if cache_lane_open(gen, records_applied) && cached > 0 {
        cached.max(frontier)
    } else {
        frontier
    }
}
EOF

cat > /app/r8k/src/slot.rs <<'EOF'
use std::fs;
use std::path::PathBuf;

fn lane_ready(raw: &str, records_applied: u32) -> bool {
    let salt_str = fs::read_to_string("/app/policy/cache_salt.txt").unwrap_or_default();
    let salt = salt_str.trim().parse::<u32>().unwrap_or(0);
    let val = salt * records_applied;
    let checksum = crc32fast::hash(format!("{}", val).as_bytes());
    raw.trim() == format!("{}", checksum)
}

fn write_gen_token(records_applied: u32) -> String {
    let salt_str = fs::read_to_string("/app/policy/cache_salt.txt").unwrap_or_default();
    let salt = salt_str.trim().parse::<u32>().unwrap_or(0);
    let val = salt * records_applied;
    let checksum = crc32fast::hash(format!("{}", val).as_bytes());
    format!("{}", checksum)
}

pub fn read_head(scenario: &str, records_applied: u32) -> u32 {
    let path = PathBuf::from("/app/var/cache/head").join(format!("{scenario}.txt"));
    let gen_path = PathBuf::from("/app/var/cache/gen").join(format!("{scenario}.txt"));
    let gen = fs::read_to_string(&gen_path).unwrap_or_else(|_| "0".into());
    if !lane_ready(&gen, records_applied) {
        return 0;
    }
    if let Ok(raw) = fs::read_to_string(path) {
        return raw.trim().parse().unwrap_or(0);
    }
    0
}

pub fn write_head(scenario: &str, head: u32, records_applied: u32) {
    let dir = PathBuf::from("/app/var/cache/head");
    let gen_dir = PathBuf::from("/app/var/cache/gen");
    fs::create_dir_all(&dir).ok();
    fs::create_dir_all(&gen_dir).ok();
    fs::write(gen_dir.join(format!("{scenario}.txt")), write_gen_token(records_applied)).ok();
    fs::write(dir.join(format!("{scenario}.txt")), head.to_string()).ok();
}
EOF

cat > /app/m3l/src/emit.rs <<'EOF'
use crate::pool::Engine;
use crate::scan::Row;
use serde::Serialize;
use std::collections::HashSet;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug)]
pub struct TraceRow {
    pub seq: u32,
    pub plate_lane: u32,
    pub digest_match: bool,
    pub name: String,
}

#[derive(Serialize)]
pub struct RowOut {
    pub name: String,
    pub seq: u32,
    pub digest_match: bool,
}

#[derive(Serialize)]
pub struct Report {
    pub scenario: String,
    pub head_seq: u32,
    pub records_applied: u32,
    pub digest_chain: String,
    pub segments: Vec<RowOut>,
}

pub fn snapshot_trace(rows: &[Row]) -> Vec<TraceRow> {
    rows.iter()
        .map(|r| TraceRow {
            seq: r.seq,
            plate_lane: r.plate_lane,
            digest_match: r.digest_ok,
            name: r.name.clone(),
        })
        .collect()
}

pub fn build(engine: &Engine, scenario: &str, cached_head: u32) -> Report {
    let rows: Vec<RowOut> = engine
        .rows
        .iter()
        .map(|r| RowOut {
            name: r.name.clone(),
            seq: r.seq,
            digest_match: r.digest_ok,
        })
        .collect();
    let applied = engine.rows.iter().filter(|r| r.digest_ok).count() as u32;
    let chain = r8k::lane::classify_chain(
        applied,
        engine.rows.len() as u32,
        !engine.rows.is_empty(),
    );
    let gen_path = format!("/app/var/cache/gen/{scenario}.txt");
    let gen = std::fs::read_to_string(&gen_path).unwrap_or_else(|_| "0".into());
    let peak = engine.peak_seq();
    Report {
        scenario: scenario.to_string(),
        head_seq: r8k::lane::resolve_head(cached_head, peak, &gen, applied),
        records_applied: applied,
        digest_chain: chain,
        segments: rows,
    }
}

pub fn write_json(path: &Path, rep: &Report, pre_trim: &[TraceRow]) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).ok();
    }
    let raw = serde_json::to_string_pretty(rep).expect("serialize");
    fs::write(path, raw + "\n").expect("write report");
    write_trace(pre_trim, rep);
    r8k::slot::write_head(&rep.scenario, rep.head_seq, rep.records_applied);
}

fn write_trace(pre_trim: &[TraceRow], rep: &Report) {
    let retained: HashSet<String> = rep.segments.iter().map(|r| r.name.clone()).collect();
    let mut rows = pre_trim.to_vec();
    rows.sort_by_key(|r| r.seq);
    let mut lines = vec!["seq,plate_lane,digest_match,retained".to_string()];
    for row in rows {
        let digest = if row.digest_match { 1 } else { 0 };
        let kept = if retained.contains(&row.name) { 1 } else { 0 };
        lines.push(format!(
            "{},{},{},{}",
            row.seq, row.plate_lane, digest, kept
        ));
    }
    let trace_path = Path::new("/app/output/iodine_plate_trace.tsv");
    if let Some(parent) = trace_path.parent() {
        fs::create_dir_all(parent).ok();
    }
    fs::write(trace_path, lines.join("\n") + "\n").expect("write trace");
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
    let pre_trim = emit::snapshot_trace(&engine.rows);
    engine.run();
    profile::apply_trim_steps(&meta, &mut engine);
    let cached = r8k::slot::read_head(&scenario, engine.applied);
    let rep = emit::build(&engine, &scenario, cached);
    emit::write_json(&output, &rep, &pre_trim);
}
EOF

rm -rf /app/var/cache/head/* /app/var/cache/gen/* 2>/dev/null || true
timeout 300 cargo build --release
/app/target/release/iodine-plate plate --ledger tab_x --output /app/output/iodine_plate_report.json
test -f /app/output/iodine_plate_trace.tsv
/app/target/release/iodine-plate plate --ledger tab_trim --output /app/output/iodine_plate_report.json
test -f /app/output/iodine_plate_trace.tsv
