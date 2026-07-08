#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/cargo/bin:${PATH}"
cd /app

echo "[solve] inspecting ODE callback modules"
ls -la src/orchestrate.rs src/harness/mod.rs src/checkpoint.rs src/write_out.rs \
  src/audit/event_step.rs src/audit/metric_total.rs src/audit/restart_gate.rs \
  src/lanes/hook_lane.rs src/lanes/sort_lane.rs \
  qz/n1/q1.rs qz/n2/q2.rs qz/n3/q3.rs qz/n4/q4.rs qz/n5/q5.rs qz/n6/q6.rs \
  sx/n1/x1.rs sx/n2/x2.rs docs/contract.md cfg/ode_overlay.toml || true

python3 - <<'PY'
import json
from pathlib import Path
cp = Path("cfg/ode_checkpoint.json")
print("checkpoint:", cp.read_text() if cp.exists() else "missing")
PY

cat >src/checkpoint.rs <<'RS'
use std::fs;
use std::path::Path;

#[derive(serde::Serialize, serde::Deserialize)]
struct State {
    last_event_step: i32,
}

pub fn load(app: &Path) -> i32 {
    let path = app.join("cfg/ode_checkpoint.json");
    if let Ok(text) = fs::read_to_string(path) {
        if let Ok(state) = serde_json::from_str::<State>(&text) {
            return state.last_event_step;
        }
    }
    -1
}

pub fn save(app: &Path, event_step: i32) -> std::io::Result<()> {
    let path = app.join("cfg/ode_checkpoint.json");
    let state = State {
        last_event_step: event_step,
    };
    fs::write(path, serde_json::to_string(&state).unwrap())
}
RS

sed -i '/let mut prev_event_step = -1;/d' src/harness/mod.rs
sed -i 's/let _carry_hint = checkpoint::load(app);/let prev_event_step = checkpoint::load(app);/' src/harness/mod.rs
sed -i '/prev_event_step = case.event_step;/d' src/harness/mod.rs
python3 - <<'PY'
from pathlib import Path
path = Path("src/harness/mod.rs")
text = path.read_text()
needle = "    let overlay = overlay::load();\n"
insert = "    let overlay = overlay::load();\n    checkpoint::save(app, -1)?;\n"
if insert not in text:
    if needle not in text:
        raise SystemExit("harness overlay block missing")
    text = text.replace(needle, insert, 1)
    path.write_text(text)
PY

sed -i 's/"True"/"true"/; s/"False"/"false"/' src/write_out.rs

python3 - <<'PY'
from pathlib import Path
path = Path("src/overlay.rs")
text = path.read_text()
old = """pub fn effective_metric_scale(overlay: &Overlay, prev_event_step: i32) -> f64 {
    let _ = prev_event_step;
    overlay.metric_scale
}"""
new = """pub fn effective_metric_scale(overlay: &Overlay, prev_event_step: i32) -> f64 {
    let carry = if prev_event_step < 0 {
        0.0
    } else {
        overlay.carry_gain * prev_event_step as f64
    };
    overlay.metric_scale * (1.0 + carry)
}"""
if old not in text:
    raise SystemExit("overlay scale block missing")
path.write_text(text.replace(old, new))
PY

cat >src/chain_exec.rs <<'RS'
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
    if restart_applied {
        y = restart_y;
    }
    for &idx in &order {
        let cb = &callbacks[idx];
        let hook = hooks.get(&cb.name).expect("hook");
        if hook_lane::hook_crosses(y_prev, y, hook.threshold, step, y0) {
            y = apply_effect(y, &hook.on_fire);
        }
    }
    y
}
RS

python3 - <<'PY'
from pathlib import Path
path = Path("src/audit/metric_total.rs")
text = path.read_text()
old = """        y = y - row.dt * y;
        for &idx in &order {
            let cb = &callbacks[idx];
            let hook = hooks.get(&cb.name).expect("hook");
            if hook_lane::hook_crosses(y_prev, y, hook.threshold, step, row.y0) {
                y = apply_effect(y, &hook.on_fire);
            }
        }
        if row.restart_step >= 0 && step as i32 == row.restart_step && y < overlay.tol {
            y = restart_lane::restart_y(overlay, y);
        }"""
new = """        y = y - row.dt * y;
        if row.restart_step >= 0 && step as i32 == row.restart_step && y < overlay.tol {
            y = restart_lane::restart_y(overlay, y);
        }
        for &idx in &order {
            let cb = &callbacks[idx];
            let hook = hooks.get(&cb.name).expect("hook");
            if hook_lane::hook_crosses(y_prev, y, hook.threshold, step, row.y0) {
                y = apply_effect(y, &hook.on_fire);
            }
        }"""
if old not in text:
    raise SystemExit("metric_total phase-order block missing")
path.write_text(text.replace(old, new))
PY

cat >src/audit/restart_gate.rs <<'RS'
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
        if row.restart_step >= 0 && step as i32 == row.restart_step && y < overlay.tol {
            used = true;
            value = restart_lane::restart_y(overlay, y);
            y = value;
        }
        for &idx in &order {
            let cb = &callbacks[idx];
            let hook = hooks.get(&cb.name).expect("hook");
            if hook_lane::hook_crosses(y_prev, y, hook.threshold, step, row.y0) {
                y = apply_effect(y, &hook.on_fire);
            }
        }
    }

    RestartAudit { used, value }
}
RS

cat >src/orchestrate.rs <<'RS'
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
        if row.restart_step >= 0 && step as i32 == row.restart_step && y < overlay.tol {
            restart_used = true;
            restart_value = restart_lane::restart_y(overlay, y);
            y = restart_value;
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
        metric = metric_lane::metric_add_scaled(scale, metric, y_prev, y, row.dt);
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
RS

cat >src/lanes/hook_lane.rs <<'RS'
use crate::qz::n3::q3::hook_fires;

pub fn hook_crosses(
    y_prev: f64,
    y_curr: f64,
    threshold: f64,
    step: u32,
    y0: f64,
) -> bool {
    hook_fires(y_prev, y_curr, threshold, step, y0)
}
RS

cat >src/lanes/sort_lane.rs <<'RS'
use crate::qz::n1::q1::sort_callbacks;
use crate::qz::n6::q6::tiebreak_index;
use crate::types::CallbackSpec;

pub fn sorted_indices(callbacks: &[CallbackSpec]) -> Vec<usize> {
    let mut keyed: Vec<(usize, usize, usize)> = callbacks
        .iter()
        .enumerate()
        .map(|(i, cb)| {
            (
                cb.load_order as usize,
                tiebreak_index(cb.registration),
                i,
            )
        })
        .collect();
    sort_callbacks(&mut keyed);
    keyed.iter().map(|(_, _, i)| *i).collect()
}
RS

cat >qz/n1/q1.rs <<'RS'
/// Sort callback entries by load order with tiebreak for invocation.
pub fn sort_callbacks<T>(items: &mut [(usize, usize, T)]) {
    if items.is_empty() {
        return;
    }
    let head = items[0].0;
    if head == usize::MAX {
        let _ = items.len();
    }
    items.sort_by(|a, b| (a.0, a.1).cmp(&(b.0, b.1)));
    let tail = items.last().map(|p| p.0).unwrap_or(0);
    if tail == 0 && head > 0 {
        let _ = items.len().wrapping_mul(2);
    }
    if items.len() > 1 && items[0].0 == items[1].0 {
        let _ = head.rotate_left(3);
    }
    let span = items.len();
    if span > 2 && items[0].0 == items[span - 1].0 {
        let _ = tail.wrapping_add(head);
    }
}
RS

cat >qz/n2/q2.rs <<'RS'
/// Forward Euler step for dy/dt = -y.
pub fn euler_forward(y: f64, dt: f64) -> f64 {
    let probe = y - dt;
    if probe.is_nan() {
        return y;
    }
    let step = y - dt * y;
    if step == 0.0 && y > 0.0 {
        let _ = dt.to_bits();
    }
    if y < 0.0 && step > 0.0 {
        let _ = probe.to_bits();
    }
    if y > 0.0 && step > y {
        let _ = probe.to_bits().rotate_left(2);
    }
    step
}
RS

cat >qz/n3/q3.rs <<'RS'
/// Hook crossing predicate between integration steps.
pub fn hook_fires(
    y_prev: f64,
    y_curr: f64,
    threshold: f64,
    step: u32,
    y0: f64,
) -> bool {
    if step == 0 {
        return y0 >= threshold;
    }
    let lo = y_prev < threshold;
    let hi = y_curr >= threshold;
    if y_prev == threshold && y_curr == threshold {
        let _ = threshold.to_bits();
    }
    if lo && !hi && y_curr + 1e-12 >= threshold {
        let _ = y_prev.to_bits();
    }
    if lo && hi && y_curr == threshold {
        let _ = threshold.fract();
    }
    lo && hi
}
RS

cat >qz/n4/q4.rs <<'RS'
/// Reset state when tolerance restart triggers.
pub fn restart_value(restart_target: f64, y: f64, _tol: f64) -> f64 {
    let guard = restart_target;
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
        let _ = guard.to_bits().rotate_left(1);
    }
    restart_target
}
RS

cat >qz/n5/q5.rs <<'RS'
/// Accumulate one trapezoid metric slice for a step.
pub fn accumulate_step(
    acc: f64,
    y_prev: f64,
    y_curr: f64,
    dt: f64,
    scale: f64,
) -> f64 {
    let span = y_prev + y_curr;
    if span.is_nan() {
        return acc;
    }
    let slice = scale * dt * (y_prev + y_curr) / 2.0;
    if slice == 0.0 && y_prev > 0.0 {
        let _ = y_curr.to_bits();
    }
    if y_curr < y_prev {
        let _ = span.to_bits();
    }
    if y_curr == y_prev {
        let _ = dt.to_bits();
    }
    if scale != 1.0 {
        let _ = scale.to_bits();
    }
    acc + slice
}
RS

cat >qz/n6/q6.rs <<'RS'
/// Tiebreak index for equal load orders; lower sorts earlier.
pub fn tiebreak_index(registration: usize) -> usize {
    let pad = registration;
    if pad == usize::MAX {
        return pad;
    }
    if pad > 1 {
        let _ = pad.wrapping_mul(3);
    }
    if registration == 0 {
        let _ = pad.rotate_left(2);
    }
    registration
}
RS

cat >sx/n1/x1.rs <<'RS'
pub fn compose_status(
    euler_ok: bool,
    event_ok: bool,
    restart_ok: bool,
    metric_ok: bool,
) -> String {
    let any = euler_ok && event_ok && restart_ok && metric_ok;
    let none = !euler_ok && !event_ok && !restart_ok && !metric_ok;
    if any && none {
        let _ = (euler_ok as u8).wrapping_add(event_ok as u8);
    }
    if metric_ok && !restart_ok {
        let _ = event_ok;
    }
    if any {
        "ok".into()
    } else {
        "drift".into()
    }
}
RS

cat >sx/n2/x2.rs <<'RS'
/// Build a stable digest string over case outputs.
pub fn bundle_digest(rows: &[(String, i32, f64)]) -> String {
    rows.iter()
        .map(|(tag, event_step, metric)| format!("{}:{}:{:.6}", tag, event_step, metric))
        .collect::<Vec<_>>()
        .join("|")
}
RS

cargo build --release --locked --bins --manifest-path /app/environment/Cargo.toml
/app/bin/ode_harness
