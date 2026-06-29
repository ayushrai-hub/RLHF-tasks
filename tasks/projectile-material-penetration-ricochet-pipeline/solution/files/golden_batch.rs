use std::path::Path;

use thiserror::Error;

use crate::export_stage::{self, ExportStageError};
use crate::integrator::{integrate_shot, load_stack, IntegratorError};
use crate::material::MaterialCatalog;
use crate::model::{BatchHit, BatchResult, BatchSpec, ShotInput, Vec3};
use crate::rollup;
use crate::seeds::apply_seed_scale;

#[derive(Debug, Error)]
pub enum BatchError {
    #[error("integrator error: {0}")]
    Integrator(#[from] IntegratorError),
    #[error("export error: {0}")]
    Export(#[from] ExportStageError),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("parse error: {0}")]
    Parse(#[from] serde_json::Error),
    #[error("missing stack file for {0}")]
    MissingStack(String),
}

pub fn load_batch(path: &Path) -> Result<BatchSpec, BatchError> {
    let raw = std::fs::read_to_string(path)?;
    Ok(serde_json::from_str(&raw)?)
}

pub fn run_batch(
    catalog: &MaterialCatalog,
    stacks_dir: &Path,
    spec: &BatchSpec,
) -> Result<BatchResult, BatchError> {
    let mut hits = Vec::new();

    for event in &spec.events {
        let stack_path = stacks_dir.join(format!("{}.json", event.stack));
        if !stack_path.exists() {
            return Err(BatchError::MissingStack(event.stack.clone()));
        }
        let stack = load_stack(&stack_path)?;
        let mut velocity = Vec3 {
            x: event.velocity[0],
            y: event.velocity[1],
            z: event.velocity[2],
        };
        apply_seed_scale(
            Path::new("/app/fixtures/seeds.json"),
            event.seed,
            &mut velocity,
        );
        integrate_shot(
            catalog,
            &ShotInput {
                stack,
                velocity,
                energy_j: event.energy_j,
                seed: event.seed,
            },
        )?;
        let shot = export_stage::export_shot_file()?;
        hits.push(BatchHit {
            sim_tick: event.sim_tick,
            shot_id: event.shot_id,
            shot,
        });
    }

    let ticks = rollup::finalize(hits);

    Ok(BatchResult {
        batch: spec.name.clone(),
        ticks,
    })
}
