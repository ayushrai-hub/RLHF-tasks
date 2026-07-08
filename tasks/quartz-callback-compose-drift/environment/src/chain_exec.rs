use crate::audit::integrator;
use crate::lanes::hook_lane;
use crate::types::{FireEffect, HookDef};
use std::collections::HashMap;

fn apply_effect(y: f64, effect: &Option<FireEffect>) -> f64 {
    match effect {
        Some(FireEffect::Add(v)) => y + v,
        Some(FireEffect::Mul(v)) => y * v,
        Some(FireEffect::Set(v)) => *v,
        None => y,
    }
}

pub fn chain_step(
    y_prev: f64,
    y_post_euler: f64,
    restart_applied: bool,
    restart_y: f64,
    callback_order: &str,
    hooks: &HashMap<String, HookDef>,
    step: u32,
    y0: f64,
) -> f64 {
    let callbacks = integrator::parse_callbacks(callback_order);
    let order = crate::lanes::sort_lane::sorted_indices(&callbacks);
    let mut y = y_post_euler;
    let y_cross = y;
    for &idx in &order {
        let cb = &callbacks[idx];
        let hook = hooks.get(&cb.name).expect("hook");
        if hook_lane::hook_crosses(y_prev, y_cross, hook.threshold, step, y0) {
            y = apply_effect(y, &hook.on_fire);
        }
    }
    if restart_applied {
        y = restart_y;
    }
    y
}
