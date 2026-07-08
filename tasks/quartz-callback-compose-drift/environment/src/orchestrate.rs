use crate::audit::integrator;
use crate::lanes::{euler_lane, hook_lane, metric_lane, restart_lane, sort_lane, summary_lane};
use crate::overlay::Overlay;
use crate::types::{CaseOut, FireEffect, HookDef, PlanRow};
use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct SimOut {
    pub event_step: i32,
    pub metric_integral: f64,
    pub final_y: f64,
    pub restart_used: bool,
    pub restart_value: f64,
}

fn apply_effect(y: f64, effect: &Option<FireEffect>) -> f64 {
    match effect {
        Some(FireEffect::Add(v)) => y + v,
        Some(FireEffect::Mul(v)) => y * v,
        Some(FireEffect::Set(v)) => *v,
        None => y,
    }
}

pub fn run_sim(
    row: &PlanRow,
    hooks: &HashMap<String, HookDef>,
    overlay: &Overlay,
    prev_event_step: i32,
) -> SimOut {
    let callbacks = integrator::parse_callbacks(&row.callback_order);
    let order = sort_lane::sorted_indices(&callbacks);
    let mut y = row.y0;
    let mut event_step: Option<i32> = None;
    let mut metric = 0.0;
    let mut restart_used = false;
    let mut restart_value = overlay.restart_target;
    let scale = metric_lane::row_scale(overlay, prev_event_step);

    for step in 0..row.steps {
        let y_prev = y;
        y = euler_lane::euler_step(y, row.dt);
        let y_cross = y;
        for &idx in &order {
            let cb = &callbacks[idx];
            let hook = hooks.get(&cb.name).expect("hook");
            if hook_lane::hook_crosses(y_prev, y_cross, hook.threshold, step, row.y0) {
                if event_step.is_none() {
                    event_step = Some(step as i32);
                }
                y = apply_effect(y, &hook.on_fire);
            }
        }
        if row.restart_step >= 0 && step as i32 == row.restart_step && y < overlay.tol {
            restart_used = true;
            restart_value = restart_lane::restart_y(overlay, y);
            y = restart_value;
        }
        metric = metric_lane::metric_add_scaled(scale, metric, y_prev, y, row.dt);
        let _ = prev_event_step;
    }

    SimOut {
        event_step: event_step.unwrap_or(-1),
        metric_integral: metric,
        final_y: y,
        restart_used,
        restart_value,
    }
}

pub fn process_row(
    row: &PlanRow,
    hooks: &HashMap<String, HookDef>,
    overlay: &Overlay,
    prev_event_step: i32,
) -> CaseOut {
    let callbacks = integrator::parse_callbacks(&row.callback_order);
    let sensitive = integrator::order_sensitive(&callbacks);
    let buggy = run_sim(row, hooks, overlay, prev_event_step);

    let euler_lane_ok = {
        let mut y = row.y0;
        let mut y_ref = row.y0;
        for _ in 0..row.steps {
            y_ref = y_ref - row.dt * y_ref;
            y = euler_lane::euler_step(y, row.dt);
        }
        (y - y_ref).abs() < 1e-9
    };
    let euler_ok = euler_lane_ok;
    let event_ok = buggy.event_step
        == crate::audit::event_step::contract_event_step(row, hooks, overlay);
    let restart_audit =
        crate::audit::restart_gate::contract_restart(row, hooks, overlay);
    let restart_ok = if buggy.restart_used {
        restart_audit.used
            && (buggy.restart_value - restart_audit.value).abs() < 1e-12
    } else {
        true
    };
    let metric_ok = (buggy.metric_integral
        - crate::audit::metric_total::contract_metric(
            row,
            hooks,
            overlay,
            prev_event_step,
        ))
    .abs()
        < 1e-6;
    let summary_ok = euler_ok && event_ok && restart_ok && metric_ok;
    let report_line = summary_lane::audit_line(euler_ok, event_ok, restart_ok, metric_ok);

    CaseOut {
        tag: row.tag.clone(),
        event_step: buggy.event_step,
        metric_integral: buggy.metric_integral,
        order_sensitive: sensitive,
        euler_ok,
        event_ok,
        restart_ok,
        metric_ok,
        summary_ok,
        report_line,
    }
}
