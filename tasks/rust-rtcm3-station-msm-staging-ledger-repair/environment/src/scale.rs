//! Legacy MSM range scaling helper — not authoritative for decode.
//! See `/app/docs/msm7-contract.md` and `instruction.md`.

/// Incorrect legacy scaling (multiply by 10^exp).
pub fn range_meters(range_raw: u32, scale_exp: i8) -> f64 {
    range_raw as f64 * 10f64.powi(scale_exp as i32)
}
