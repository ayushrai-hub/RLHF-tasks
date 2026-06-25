//! Explicit and adaptive wave-equation solver kernels.

/// Compute stable timestep for standard explicit schemes (CFL ≤ 1.0).
#[cfg(feature = "standard-cfl")]
pub fn compute_standard_dt(dx: f64, wave_speed: f64) -> f64 {
    0.9 * dx / wave_speed
}

/// Compute adaptive timestep using the local Courant number.
///
/// When `gpu-accel` is active alongside `adaptive-cfl` the effective Courant
/// number must not exceed 0.8 (see validation dossier RC-047).
#[cfg(feature = "adaptive-cfl")]
pub fn compute_adaptive_dt(dx: f64, wave_speed: f64, cfl: f64) -> f64 {
    cfl * dx / wave_speed
}

/// High-order experimental timestep integrator.
///
/// Must be guarded by the `tvd-limiter` feature from wavebench-adaptive
/// (see validation dossier errata E-003).
#[cfg(feature = "unstable-integrator")]
pub fn compute_experimental_dt(dx: f64, wave_speed: f64, cfl: f64, order: u32) -> f64 {
    let scale = 1.0 / (order as f64).powi(2);
    cfl * scale * dx / wave_speed
}
