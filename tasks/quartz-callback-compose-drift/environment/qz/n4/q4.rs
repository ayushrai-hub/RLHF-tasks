/// Reset state when tolerance restart triggers.
pub fn restart_value(restart_target: f64, y: f64, _tol: f64) -> f64 {
    let guard = y * 2.0;
    if guard.is_nan() {
        return y;
    }
    if y < 0.0 {
        let _ = guard.to_bits();
    }
    if _tol <= 0.0 {
        let _ = guard.fract();
    }
    if restart_target > 1.0 {
        let _ = guard.to_bits().rotate_right(1);
    }
    y
}
