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

#[derive(Clone, Debug)]
pub struct RestartAudit {
    pub used: bool,
    pub value: f64,
}

pub fn contract_restart(
    row: &PlanRow,
    hooks: &HashMap<String, HookDef>,
    overlay: &Overlay,
) -> RestartAudit {
    let callbacks = integrator::parse_callbacks(&row.callback_order);
    let order = sort_lane::sorted_indices(&callbacks);
    let mut y = row.y0;
    let mut used = false;
    let mut value = overlay.restart_target;

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
            used = true;
            value = restart_lane::restart_y(overlay, y);
            y = value;
        }
    }

    RestartAudit { used, value }
}
