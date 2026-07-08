use crate::overlay::Overlay;
use crate::qz::n4::q4::restart_value;

pub fn restart_y(overlay: &Overlay, y: f64) -> f64 {
    restart_value(overlay.restart_target, y, overlay.tol)
}
