//! Non-authoritative legacy scale stub — decoy only; decode uses inline MSM7 math.

pub fn legacy_multiply(range_raw: u32, scale_exp: i8) -> f64 {
    range_raw as f64 * 10f64.powi(scale_exp as i32)
}
