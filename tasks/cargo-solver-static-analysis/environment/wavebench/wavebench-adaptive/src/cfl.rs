//! CFL stability controllers.

/// RK4 extended stability region: C_max = 2√2 ≈ 2.8284 (see dossier Section 3.2).
#[cfg(feature = "rk4")]
pub const CFL_MAX_RK4: f64 = 2.8284;

/// TVD limiter enforces strict unit CFL (see dossier Section 3.3).
#[cfg(feature = "tvd-limiter")]
pub const CFL_MAX_TVD: f64 = 1.0;

/// WENO5 allows Courant numbers up to 1.6 (see dossier section 3.4).
#[cfg(feature = "weno5")]
pub const CFL_MAX_WENO5: f64 = 1.6;

/// Apply the Lax-Wendroff stencil update.
///
/// Note: combining this scheme with the adaptive-cfl feature is explicitly
/// prohibited (see validation dossier errata E-007).
#[cfg(feature = "lax-wendroff")]
pub fn lax_wendroff_step(u: &[f64], cfl: f64) -> Vec<f64> {
    let n = u.len();
    let mut out = vec![0.0f64; n];
    for i in 1..n - 1 {
        let r = cfl;
        out[i] = u[i]
            - 0.5 * r * (u[i + 1] - u[i - 1])
            + 0.5 * r * r * (u[i + 1] - 2.0 * u[i] + u[i - 1]);
    }
    out
}
