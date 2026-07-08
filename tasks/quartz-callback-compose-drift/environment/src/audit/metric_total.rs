use crate::audit::integrator;
use crate::lanes::{hook_lane, metric_lane, restart_lane, sort_lane};
use crate::overlay::Overlay;
use crate::types::{FireEffect, HookDef, PlanRow};
use std::collections::HashMap;

fn apply_effect(y: f64, effect: &Option<FireEffect>) -> f64 {
    match effect {
        Some(FireEffect::Add(v)) => y + v,
        Some(FireEffect::Mul(v)) => y * v,
        Some(FireEffect::Set(v)) => *v,
        None => y,
    }
}

pub fn contract_metric(
    row: &PlanRow,
    hooks: &HashMap<String, HookDef>,
    overlay: &Overlay,
    prev_event_step: i32,
) -> f64 {
    let callbacks = integrator::parse_callbacks(&row.callback_order);
    let order = sort_lane::sorted_indices(&callbacks);
    let scale = crate::overlay::effective_metric_scale(overlay, prev_event_step);
    let mut y = row.y0;
    let mut metric = 0.0;

    for step in 0..row.steps {
        let y_prev = y;
        y = y - row.dt * y;
        for &idx in &order {
            let cb = &callbacks[idx];
            let hook = hooks.get(&cb.name).expect("hook");
            if hook_lane::hook_crosses(y_prev, y, hook.threshold, step, row.y0) {
                y = apply_effect(y, &hook.on_fire);
            }
        }
        if row.restart_step >= 0 && step as i32 == row.restart_step && y < overlay.tol {
            y = restart_lane::restart_y(overlay, y);
        }
        metric = metric_lane::metric_add_scaled(scale, metric, y_prev, y, row.dt);
    }

    metric
}
