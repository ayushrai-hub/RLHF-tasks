mod p4;
mod run_loop;
mod sim_bridge;
mod stages;

use hash_n6::{baseline_entries, chain_head};
use run_loop::SimConfig;
use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    let mut out = PathBuf::from("/app/output/failover_trace.json");
    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--output" {
            out = PathBuf::from(args.next().expect("output path"));
        }
    }

    let root = PathBuf::from("/app/environment");
    let cfg = SimConfig {
        env_root: root.clone(),
        plan_path: root.join("fixtures/plan_seed.toml"),
        controller_path: root.join("fixtures/controller_pair.toml"),
    };

    let runs = run_loop::run_all_scenarios(&cfg);
    let doc = run_loop::TraceDocument {
        audit_chain_head: chain_head(&baseline_entries()),
        runs,
    };
    if let Some(parent) = out.parent() {
        fs::create_dir_all(parent).ok();
    }
    let json = serde_json::to_string_pretty(&doc).expect("trace json");
    fs::write(out, json).expect("write trace");
}
