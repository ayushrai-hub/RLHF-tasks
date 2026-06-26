use std::env;
use std::fs;
use std::path::PathBuf;

use lend_core::{digest_lines_for_payload, probe_offsets_for_payload, replay_dir};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct StreamConfig {
    chunk_size: u16,
    digest_width: u16,
}

fn load_config() -> StreamConfig {
    let raw = fs::read_to_string("/app/config/stream.json").expect("read stream.json");
    serde_json::from_str(&raw).expect("parse stream.json")
}

fn cmd_probe_one(path: PathBuf) -> i32 {
    let cfg = load_config();
    let _width = cfg.digest_width;
    let payload = fs::read(&path).expect("read trace");
    let offsets = probe_offsets_for_payload(&payload, cfg.chunk_size as usize);
    let rendered = offsets
        .iter()
        .map(|o| o.to_string())
        .collect::<Vec<_>>()
        .join(",");
    println!("{rendered}");
    0
}

fn cmd_replay_one(path: PathBuf) -> i32 {
    let cfg = load_config();
    let payload = fs::read(&path).expect("read trace");
    let lines = digest_lines_for_payload(&payload, cfg.chunk_size as usize);
    for line in lines {
        println!("{line}");
    }
    0
}

fn cmd_replay_dir(dir: PathBuf) -> i32 {
    let cfg = load_config();
    let runs = replay_dir(&dir, cfg.chunk_size as usize).expect("replay traces");
    if runs.is_empty() {
        eprintln!("streamd: no .trace files under {}", dir.display());
        return 1;
    }
    for (name, lines) in &runs {
        if lines.is_empty() {
            eprintln!("streamd: trace {} produced no digest lines", name);
            return 1;
        }
    }
    println!("streamd: replayed {} trace(s) ok", runs.len());
    0
}

fn main() {
    let mut args = env::args().skip(1);
    let cmd = args.next().unwrap_or_else(|| {
        eprintln!("usage: streamd probe-one <trace> | replay-one <trace> | replay <dir>");
        std::process::exit(2);
    });

    match cmd.as_str() {
        "probe-one" => {
            let path = PathBuf::from(args.next().expect("trace path"));
            std::process::exit(cmd_probe_one(path));
        }
        "replay-one" => {
            let path = PathBuf::from(args.next().expect("trace path"));
            std::process::exit(cmd_replay_one(path));
        }
        "replay" => {
            let dir = PathBuf::from(args.next().expect("traces_dir"));
            std::process::exit(cmd_replay_dir(dir));
        }
        other => {
            eprintln!("unknown command: {other}");
            std::process::exit(2);
        }
    }
}
