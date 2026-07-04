use std::env;
use std::fs;
use std::path::PathBuf;

use seglog_lab::sim::emit::{render_report, render_report_subset};
use seglog_lab::sim::flows::branches_aligned;
use seglog_lab::sim::case::cases;

fn main() {
    let mut args = env::args().skip(1);
    let mode = args.next().unwrap_or_else(|| "run".to_string());
    match mode.as_str() {
        "run" => run_matrix(&mut args),
        "probe" => probe_scenario(&mut args),
        "staging-roundtrip" => staging_roundtrip(&mut args),
        "double-fold" => double_fold(&mut args),
        "orphan-checkpoint" => orphan_checkpoint(&mut args),
        other => {
            eprintln!(
                "usage: cargo run --quiet -- run --output /app/output/ledger_report.json [--scenarios a,b]\n       cargo run --quiet -- probe --scenario name\n       cargo run --quiet -- staging-roundtrip --scenario name\n       cargo run --quiet -- double-fold --scenario name\n       cargo run --quiet -- orphan-checkpoint --scenario name"
            );
            eprintln!("unknown mode: {other}");
            std::process::exit(2);
        }
    }
}

fn run_matrix(args: &mut impl Iterator<Item = String>) {
    let mut output = PathBuf::from("/app/output/ledger_report.json");
    let mut scenarios: Option<String> = None;
    while let Some(arg) = args.next() {
        if arg == "--output" {
            output = PathBuf::from(args.next().unwrap_or_else(|| output.to_string_lossy().to_string()));
        } else if arg == "--scenarios" {
            scenarios = Some(args.next().unwrap_or_default());
        }
    }
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent).expect("create report directory");
    }
    let report = if let Some(list) = scenarios {
        let names: Vec<&str> = list.split(',').map(str::trim).filter(|s| !s.is_empty()).collect();
        render_report_subset(&names)
    } else {
        render_report()
    };
    fs::write(&output, report).expect("write report");
}

fn probe_scenario(args: &mut impl Iterator<Item = String>) {
    let scenario = read_scenario(args);
    let case = find_case(&scenario);
    if branches_aligned(&case) {
        std::process::exit(0);
    }
    std::process::exit(1);
}

fn double_fold(args: &mut impl Iterator<Item = String>) {
    let scenario = read_scenario(args);
    let case = find_case(&scenario);
    if seglog_lab::sim::flows::double_fold_idempotent(&case) {
        std::process::exit(0);
    }
    std::process::exit(1);
}

fn orphan_checkpoint(args: &mut impl Iterator<Item = String>) {
    let scenario = read_scenario(args);
    let case = find_case(&scenario);
    if seglog_lab::sim::flows::orphan_checkpoint_ignored(&case) {
        std::process::exit(0);
    }
    std::process::exit(1);
}

fn read_scenario(args: &mut impl Iterator<Item = String>) -> String {
    let mut scenario = String::new();
    while let Some(arg) = args.next() {
        if arg == "--scenario" {
            scenario = args.next().unwrap_or_default();
        }
    }
    scenario
}

fn find_case(scenario: &str) -> seglog_lab::sim::case::Scenario {
    cases()
        .into_iter()
        .find(|entry| entry.name == scenario)
        .unwrap_or_else(|| {
            eprintln!("unknown scenario: {scenario}");
            std::process::exit(2);
        })
}

fn staging_roundtrip(args: &mut impl Iterator<Item = String>) {
    let scenario = read_scenario(args);
    let case = find_case(&scenario);
    if seglog_lab::sim::flows::staging_checkpoint_roundtrip(&case) {
        std::process::exit(0);
    }
    std::process::exit(1);
}
