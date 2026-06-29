use clap::{Parser, Subcommand};
use std::path::PathBuf;

use ballcore::batch::load_batch;
use ballcore::export::write_json;
use ballcore::export_stage::export_shot_file;
use ballcore::integrator::{integrate_shot, load_stack, simulate_shot};
use ballcore::material::MaterialCatalog;
use ballcore::model::{ShotInput, Vec3};
use ballcore::run_batch;
use ballcore::seeds::apply_seed_scale;

const SEEDS_PATH: &str = "/app/fixtures/seeds.json";

#[derive(Parser)]
#[command(name = "ballctl", version, about = "Projectile ballistics CLI")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Integrate one shot and write /app/state/shot-snapshot.json (no export JSON).
    IntegrateShot {
        #[arg(long)]
        stack: PathBuf,
        #[arg(long)]
        materials: PathBuf,
        #[arg(long, value_parser = parse_vec3)]
        velocity: Vec3,
        #[arg(long)]
        energy: f64,
        #[arg(long, default_value_t = 1)]
        seed: u64,
    },
    /// Read staged snapshot and write shot export JSON.
    ExportShot {
        #[arg(long)]
        export: PathBuf,
    },
    /// One-step shortcut (legacy); prefer integrate-shot then export-shot.
    SimulateShot {
        #[arg(long)]
        stack: PathBuf,
        #[arg(long)]
        materials: PathBuf,
        #[arg(long, value_parser = parse_vec3)]
        velocity: Vec3,
        #[arg(long)]
        energy: f64,
        #[arg(long, default_value_t = 1)]
        seed: u64,
        #[arg(long)]
        export: PathBuf,
    },
    SimulateBatch {
        #[arg(long)]
        batch: PathBuf,
        #[arg(long)]
        materials: PathBuf,
        #[arg(long, default_value = "/app/fixtures/stacks")]
        stacks_dir: PathBuf,
        #[arg(long)]
        export: PathBuf,
    },
}

fn parse_vec3(raw: &str) -> Result<Vec3, String> {
    let parts: Vec<&str> = raw.split(',').collect();
    if parts.len() != 3 {
        return Err("expected x,y,z".into());
    }
    Ok(Vec3 {
        x: parts[0].parse::<f64>().map_err(|e| e.to_string())?,
        y: parts[1].parse::<f64>().map_err(|e| e.to_string())?,
        z: parts[2].parse::<f64>().map_err(|e| e.to_string())?,
    })
}

fn shot_input(
    stack: PathBuf,
    materials: PathBuf,
    mut velocity: Vec3,
    energy: f64,
    seed: u64,
) -> Result<(MaterialCatalog, ShotInput), Box<dyn std::error::Error>> {
    apply_seed_scale(PathBuf::from(SEEDS_PATH).as_path(), seed, &mut velocity);
    let catalog = MaterialCatalog::load(&materials)?;
    let stack_spec = load_stack(&stack)?;
    Ok((
        catalog,
        ShotInput {
            stack: stack_spec,
            velocity,
            energy_j: energy,
            seed,
        },
    ))
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    match cli.command {
        Commands::IntegrateShot {
            stack,
            materials,
            velocity,
            energy,
            seed,
        } => {
            let (catalog, input) = shot_input(stack, materials, velocity, energy, seed)?;
            integrate_shot(&catalog, &input)?;
        }
        Commands::ExportShot { export } => {
            let result = export_shot_file()?;
            write_json(&export, &result)?;
        }
        Commands::SimulateShot {
            stack,
            materials,
            velocity,
            energy,
            seed,
            export,
        } => {
            let (catalog, input) = shot_input(stack, materials, velocity, energy, seed)?;
            let result = simulate_shot(&catalog, &input)?;
            write_json(&export, &result)?;
        }
        Commands::SimulateBatch {
            batch,
            materials,
            stacks_dir,
            export,
        } => {
            let catalog = MaterialCatalog::load(&materials)?;
            let spec = load_batch(&batch)?;
            let result = run_batch(&catalog, &stacks_dir, &spec)?;
            write_json(&export, &result)?;
        }
    }
    Ok(())
}
