use crate::audit::integrator;
use crate::lanes::{hook_lane, restart_lane, sort_lane};
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

pub fn contract_event_step(
    row: &PlanRow,
    hooks: &HashMap<String, HookDef>,
    overlay: &Overlay,
) -> i32 {
    let callbacks = integrator::parse_callbacks(&row.callback_order);
    let order = sort_lane::sorted_indices(&callbacks);
    let mut y = row.y0;
    let mut event_step: Option<i32> = None;

    for step in 0..row.steps {
        let y_prev = y;
        y = y - row.dt * y;
        if row.restart_step >= 0 && step as i32 == row.restart_step && y < overlay.tol {
            y = restart_lane::restart_y(overlay, y);
        }
        for &idx in &order {
            let cb = &callbacks[idx];
            let hook = hooks.get(&cb.name).expect("hook");
            if hook_lane::hook_crosses(y_prev, y, hook.threshold, step, row.y0) {
                if event_step.is_none() {
                    event_step = Some(step as i32);
                }
                y = apply_effect(y, &hook.on_fire);
            }
        }
    }

    event_step.unwrap_or(-1)
}
