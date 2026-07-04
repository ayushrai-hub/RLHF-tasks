mod audit_materialize;
mod cli;
mod db;
mod db_fingerprint;
mod decode;
mod export;
mod ledger;
mod persist;
mod report_metrics;
mod scale;
mod seal;
mod snapshot;
mod stage;
mod staging_manifest;
mod types;

fn main() {
    if let Err(err) = cli::run(std::env::args().skip(1).collect()) {
        eprintln!("{err}");
        std::process::exit(1);
    }
}
