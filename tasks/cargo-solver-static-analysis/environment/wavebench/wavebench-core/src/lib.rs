//! Core wave-equation solvers for the WaveBench suite.
//!
//! # Feature flags
//!
//! | Feature | Effect |
//! |---|---|
//! | `standard-cfl` | Standard explicit-scheme CFL enforcement (default) |
//! | `adaptive-cfl` | Adaptive timestep controller — activates wavebench-adaptive |
//! | `hpc-mode` | HPC cluster optimisations (enables adaptive-cfl + parallel-io) |
//! | `parallel-io` | Rayon-backed parallel I/O |
//! | `experimental` | Experimental integrators (enables adaptive-cfl + unstable-integrator) |
//! | `unstable-integrator` | High-order integrator; requires tvd-limiter guard from wavebench-adaptive |
//! | `gpu-accel` | CUDA acceleration (enables adaptive-cfl) |

pub mod solver;

#[cfg(feature = "standard-cfl")]
pub const CFL_MAX_STANDARD: f64 = 1.0;

#[cfg(feature = "adaptive-cfl")]
pub const CFL_DEFAULT_ADAPTIVE: f64 = 0.9;
