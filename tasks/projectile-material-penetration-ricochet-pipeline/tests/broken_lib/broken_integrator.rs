use thiserror::Error;

use crate::material::MaterialCatalog;
use crate::model::{
    LayerResult, RicochetResult, ShotInput, ShotResult, StackSpec, Vec3,
};
use crate::ricochet::compute_ricochet;

const PEN_K: f64 = 75_000.0;
const EPS: f64 = 1e-9;

#[derive(Debug, Error)]
pub enum IntegratorError {
    #[error("material error: {0}")]
    Material(#[from] crate::material::MaterialError),
    #[error("empty stack")]
    EmptyStack,
}

pub fn simulate_shot(
    catalog: &MaterialCatalog,
    input: &ShotInput,
) -> Result<ShotResult, IntegratorError> {
    let stack = &input.stack;
    if stack.layers.is_empty() {
        return Err(IntegratorError::EmptyStack);
    }

    let normal = Vec3 {
        x: stack.normal[0],
        y: stack.normal[1],
        z: stack.normal[2],
    };

    let mut energy = input.energy_j;
    let mut ledger = 0.0_f64;
    let mut layers_out = Vec::new();
    let mut ricochet: Option<RicochetResult> = None;
    let mut penetrated = true;

    for (idx, layer) in stack.layers.iter().enumerate() {
        let mat = catalog.by_physics_id(layer.physics_id)?;
        energy *= mat.falloff;

        let max_depth = energy / (mat.hardness * PEN_K);
        let depth = max_depth.min(layer.thickness_m);

        if depth + EPS < layer.thickness_m {
            penetrated = false;
            ricochet = Some(compute_ricochet(input.velocity, normal));
            layers_out.push(LayerResult {
                physics_id: layer.physics_id,
                depth_m: round6(depth),
                fully_penetrated: false,
                energy_after_j: round3(energy),
            });
            break;
        }

        ledger += layer.thickness_m;
        if idx + 1 < stack.layers.len() {
            ledger += layer.thickness_m;
        }

        layers_out.push(LayerResult {
            physics_id: layer.physics_id,
            depth_m: round6(layer.thickness_m),
            fully_penetrated: true,
            energy_after_j: round3(energy),
        });
    }

    Ok(ShotResult {
        stack: stack.name.clone(),
        seed: input.seed,
        path_ledger_m: round6(ledger),
        exit_energy_j: round3(energy),
        penetrated,
        layers: layers_out,
        ricochet,
    })
}

pub fn load_stack(path: &std::path::Path) -> Result<StackSpec, IntegratorError> {
    let raw = std::fs::read_to_string(path).map_err(|e| {
        IntegratorError::Material(crate::material::MaterialError::Io(e))
    })?;
    serde_json::from_str(&raw).map_err(|e| {
        IntegratorError::Material(crate::material::MaterialError::Parse(e))
    })
}

fn round3(v: f64) -> f64 {
    (v * 1000.0).round() / 1000.0
}

fn round6(v: f64) -> f64 {
    (v * 1_000_000.0).round() / 1_000_000.0
}
