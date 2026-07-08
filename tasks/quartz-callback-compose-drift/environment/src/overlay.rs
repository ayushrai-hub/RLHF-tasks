use std::fs;

pub struct Overlay {
    pub tol: f64,
    pub metric_scale: f64,
    pub restart_target: f64,
    pub carry_gain: f64,
}

pub fn effective_metric_scale(overlay: &Overlay, prev_event_step: i32) -> f64 {
    let _ = prev_event_step;
    overlay.metric_scale
}

pub fn load() -> Overlay {
    let text = fs::read_to_string("/app/cfg/ode_overlay.toml").unwrap_or_default();
    let mut tol = 1e-6;
    let mut metric_scale = 1.0;
    let mut restart_target = 1.0;
    let mut carry_gain = 0.005;
    for line in text.lines() {
        if let Some((k, v)) = line.split_once('=') {
            match k.trim() {
                "tol" => tol = v.trim().parse().unwrap_or(1e-6),
                "metric_scale" => metric_scale = v.trim().parse().unwrap_or(1.0),
                "restart_target" => restart_target = v.trim().parse().unwrap_or(1.0),
                "carry_gain" => carry_gain = v.trim().parse().unwrap_or(0.005),
                _ => {}
            }
        }
    }
    Overlay {
        tol,
        metric_scale,
        restart_target,
        carry_gain,
    }
}
