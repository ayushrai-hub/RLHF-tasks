mod config;
mod journal;
mod relay;
mod stages;
mod packet;
mod reconcile;
mod metrics;
mod report;
mod frame;
mod constants;
mod checksum;

use clap::Parser;
use std::fs;

#[derive(Parser)]
#[command(name = "relay-audit")]
struct Args {
    #[arg(long)]
    config: String,
    #[arg(long)]
    journal: String,
    #[arg(long)]
    output: String,
}

fn main() {
    let args = Args::parse();
    let cfg = config::load_config(&args.config);
    let entries = journal::load_journal(&args.journal);
    let packets = relay::replay_journal(&entries, &cfg);
    let processed = stages::apply_pipeline(&packets, &cfg);
    let reconciled = reconcile::cross_validate(&processed, &cfg);
    let summary = metrics::compute_metrics(&reconciled, &cfg);
    let output = report::build_report(reconciled, summary);
    fs::create_dir_all(std::path::Path::new(&args.output).parent().unwrap()).ok();
    fs::write(&args.output, serde_json::to_string_pretty(&output).unwrap())
        .expect("cannot write output");
}
