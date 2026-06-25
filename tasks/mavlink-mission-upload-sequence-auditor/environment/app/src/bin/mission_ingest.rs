use std::path::PathBuf;

use clap::Parser;

use mission_audit::ingest;

#[derive(Parser)]
#[command(name = "mission-ingest")]
struct Cli {
    #[arg(long)]
    db: PathBuf,
    #[arg(long)]
    log: PathBuf,
    #[arg(long)]
    upload_id: String,
    #[arg(long)]
    vehicle: String,
    #[arg(long, default_value = "/app/config/vehicle-profile.json")]
    profile: PathBuf,
}

fn main() {
    let cli = Cli::parse();
    let _ = cli.profile;
    if let Err(err) = ingest::run(ingest::Options {
        db_path: &cli.db,
        log_path: &cli.log,
        upload_id: &cli.upload_id,
        vehicle_id: &cli.vehicle,
    }) {
        eprintln!("{err}");
        std::process::exit(1);
    }
}
