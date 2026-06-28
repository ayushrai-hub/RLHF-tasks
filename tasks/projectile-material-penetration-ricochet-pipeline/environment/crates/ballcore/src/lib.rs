//! Ballistics core library for material-stack penetration simulation.

pub mod batch;
pub mod digest;
pub mod export;
pub mod export_stage;
pub mod falloff;
pub mod ingest;
pub mod integrator;
pub mod material;
pub mod model;
pub mod publish;
pub mod replay_gate;
pub mod ricochet;
pub mod rollup;
pub mod seeds;
pub mod staging;

pub use batch::{load_batch, run_batch};
pub use export_stage::export_shot_file;
pub use integrator::{integrate_shot, simulate_shot};
pub use material::MaterialCatalog;
pub use model::{BatchSpec, ShotInput, ShotResult, StackSpec};
