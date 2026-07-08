use crate::overlay::Overlay;
use crate::qz::n5::q5::accumulate_step;

pub fn metric_add(
    overlay: &Overlay,
    acc: f64,
    y_prev: f64,
    y_curr: f64,
    dt: f64,
) -> f64 {
    accumulate_step(acc, y_prev, y_curr, dt, overlay.metric_scale)
}

pub fn metric_add_scaled(
    scale: f64,
    acc: f64,
    y_prev: f64,
    y_curr: f64,
    dt: f64,
) -> f64 {
    accumulate_step(acc, y_prev, y_curr, dt, scale)
}

pub fn row_scale(overlay: &Overlay, prev_event_step: i32) -> f64 {
    crate::overlay::effective_metric_scale(overlay, prev_event_step)
}
