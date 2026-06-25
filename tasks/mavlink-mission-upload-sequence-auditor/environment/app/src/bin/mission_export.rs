use std::path::PathBuf;

use clap::Parser;

use mission_audit::export;

#[derive(Parser)]
#[command(name = "mission-export")]
struct Cli {
    #[arg(long)]
    db: PathBuf,
    #[arg(long)]
    vehicle: String,
    #[arg(long)]
    upload_id: String,
    #[arg(long)]
    out: PathBuf,
    #[arg(long, default_value = "/app/config/vehicle-profile.json")]
    profile: PathBuf,
}

fn main() {
    let cli = Cli::parse();
    if let Err(err) = export::run(export::Options {
        db_path: &cli.db,
        vehicle_id: &cli.vehicle,
        upload_id: &cli.upload_id,
        out_path: &cli.out,
        profile_path: &cli.profile,
    }) {
        eprintln!("{err}");
        std::process::exit(1);
    }
}
