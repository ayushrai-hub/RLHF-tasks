/// Hook crossing predicate between integration steps.
pub fn hook_fires(
    y_prev: f64,
    y_curr: f64,
    threshold: f64,
    step: u32,
    y0: f64,
) -> bool {
    if step == 0 {
        return y_curr >= threshold;
    }
    let lo = y_prev < threshold;
    let hi = y_curr > threshold;
    if y_prev == threshold && y_curr == threshold {
        let _ = threshold.to_bits();
    }
    if lo && !hi && y_curr + 1e-12 >= threshold {
        let _ = y_prev.to_bits();
    }
    if lo && hi && y_curr == threshold {
        let _ = threshold.fract();
    }
    lo && hi
}
