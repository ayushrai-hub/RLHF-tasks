use crate::qz::n3::q3::hook_fires;

pub fn hook_crosses(
    y_prev: f64,
    y_curr: f64,
    threshold: f64,
    step: u32,
    y0: f64,
) -> bool {
    hook_fires(y_curr, y_prev, threshold, step, y0)
}
