#!/usr/bin/env bash
set -euo pipefail

DISPATCHER_DIR=/app/task_file/dispatcher

cat > "$DISPATCHER_DIR/src/dispatch.rs" << 'RUST'
use std::collections::HashMap;

use crate::types::{Allocation, Config, Dispatch, Unit};

const DROOP: f64 = 0.5;
const FREQ_GAIN: f64 = 8.0;
const DAMP: f64 = 1.1;
const JITTER: f64 = 0.05;
const NEAR_LO: f64 = 0.40;
const NEAR_HI: f64 = 0.50;
const FREQ_MIN: f64 = 49.0;
const FREQ_MAX: f64 = 51.0;
const EPS: f64 = 1e-6;

fn is_renewable(fuel: &str) -> bool {
    fuel == "solar" || fuel == "wind"
}
fn is_sync(fuel: &str) -> bool {
    fuel == "gas" || fuel == "diesel"
}

pub fn dispatch(units: &[Unit], config: &Config) -> Dispatch {
    let n = units.len();
    let demand = config.total_demand_kw;
    let res_req = config.reserve_requirement_kw;
    let nominal = config.nominal_frequency;
    let cap = config.max_committed_thermal;
    // Aim a hair above demand: enough to clear the demand floor with a small,
    // service-friendly oversupply margin.
    let target = demand * 1.006;

    let ac: Vec<f64> = units.iter().map(|u| u.capacity_kw * u.avail).collect();
    let id_idx: HashMap<&str, usize> =
        units.iter().enumerate().map(|(i, u)| (u.id.as_str(), i)).collect();

    let mut conflicts: Vec<Vec<usize>> = vec![Vec::new(); n];
    for pair in &config.conflict_pairs {
        if pair.len() == 2 {
            if let (Some(&a), Some(&b)) =
                (id_idx.get(pair[0].as_str()), id_idx.get(pair[1].as_str()))
            {
                conflicts[a].push(b);
                conflicts[b].push(a);
            }
        }
    }
    let mandatory: Vec<usize> = config
        .mandatory_online_units
        .iter()
        .filter_map(|s| id_idx.get(s.as_str()).copied())
        .collect();

    let mut f = vec![0.0_f64; n];
    let mut r = vec![0.0_f64; n];

    let conf_cap = |f: &[f64], i: usize| -> f64 {
        if conflicts[i].iter().any(|&p| f[p] > 0.5) { 0.5 } else { 1.0 }
    };
    let supply = |f: &[f64]| -> f64 { (0..n).map(|i| ac[i] * f[i]).sum() };

    // Phase A: renewables as high as conflicts allow (biggest first).
    let mut renew: Vec<usize> = (0..n).filter(|&i| is_renewable(&units[i].fuel)).collect();
    renew.sort_by(|&a, &b| ac[b].partial_cmp(&ac[a]).unwrap());
    for &i in &renew {
        f[i] = conf_cap(&f, i);
    }
    // Phase B: batteries hard (0.95) — clean and they free no commitment slots.
    for i in 0..n {
        if units[i].fuel == "battery" {
            f[i] = conf_cap(&f, i).min(0.95);
        }
    }
    // Mandatory online at min_stable.
    for &i in &mandatory {
        if f[i] < units[i].min_stable {
            f[i] = units[i].min_stable;
        }
    }

    // Phase C: choose the committed thermal set while respecting the commitment
    // cap and preserving enough margin for the score thresholds.
    let mandatory_thermal: Vec<usize> =
        mandatory.iter().copied().filter(|&i| is_sync(&units[i].fuel)).collect();
    let mut committed: Vec<bool> = vec![false; n];
    for &i in &mandatory_thermal {
        committed[i] = true;
    }
    let mut cand: Vec<usize> = (0..n)
        .filter(|&i| units[i].fuel == "gas" && !units[i].degraded && !committed[i])
        .collect();
    cand.sort_by(|&a, &b| {
        ac[b]
            .partial_cmp(&ac[a])
            .unwrap()
            .then(units[a].emission_rate.partial_cmp(&units[b].emission_rate).unwrap())
    });
    let budget = cap.saturating_sub(mandatory_thermal.len());
    for &i in cand.iter().take(budget) {
        committed[i] = true;
    }
    let committed_idx: Vec<usize> = (0..n).filter(|&i| committed[i]).collect();

    // Water-fill the committed set by marginal emission until demand is covered.
    for _ in 0..60000 {
        if target - supply(&f) <= 0.0 {
            break;
        }
        let mut best: Option<usize> = None;
        let mut best_marg = f64::INFINITY;
        for &i in &committed_idx {
            let cc = conf_cap(&f, i);
            if f[i] >= cc - 1e-9 {
                continue;
            }
            let marg = units[i].emission_rate * (1.0 + 1.2 * f[i]);
            if marg < best_marg {
                best_marg = marg;
                best = Some(i);
            }
        }
        match best {
            Some(i) => {
                let cc = conf_cap(&f, i);
                f[i] = (f[i] + 4.0 / ac[i]).min(cc);
            }
            None => break,
        }
    }

    // Reserve: batteries first (responsiveness 1.0), then UNCOMMITTED thermal held
    // as standby (dispatch_fraction stays 0, so they consume no commitment slot),
    // biggest responsive headroom first.
    for i in 0..n {
        if units[i].fuel == "battery" {
            r[i] = 1.0;
        }
    }
    let reserve_total = |f: &[f64], r: &[f64]| -> f64 {
        (0..n).map(|i| ac[i] * (1.0 - f[i]) * units[i].responsiveness * r[i]).sum()
    };
    let mut standby: Vec<usize> = (0..n)
        .filter(|&i| is_sync(&units[i].fuel) && f[i] < EPS)
        .collect();
    standby.sort_by(|&a, &b| {
        (ac[b] * units[b].responsiveness)
            .partial_cmp(&(ac[a] * units[a].responsiveness))
            .unwrap()
    });
    for &i in &standby {
        if reserve_total(&f, &r) >= res_req {
            break;
        }
        r[i] = 1.0;
    }

    // Frequency setpoint = the settled frequency this dispatch produces.
    let s = supply(&f);
    let imbalance = (s - demand) / demand;
    let rr = (reserve_total(&f, &r) / res_req.max(1e-9)).min(1.5);
    let mut near = 0.0_f64;
    for pair in &config.conflict_pairs {
        if let (Some(&a), Some(&b)) =
            (id_idx.get(pair[0].as_str()), id_idx.get(pair[1].as_str()))
        {
            if f[a] >= NEAR_LO && f[a] <= NEAR_HI && f[b] >= NEAR_LO && f[b] <= NEAR_HI {
                near += 1.0;
            }
        }
    }
    let sync: f64 = (0..n).filter(|&i| is_sync(&units[i].fuel)).map(|i| ac[i] * f[i]).sum();
    let inertia = sync / s.max(1e-9);
    let mut fset = nominal - DROOP * (1.0 - inertia) + FREQ_GAIN * imbalance / (1.0 + DAMP * rr)
        + JITTER * near;
    fset = fset.clamp(FREQ_MIN, FREQ_MAX);

    let allocations = (0..n)
        .map(|i| Allocation {
            unit_id: units[i].id.clone(),
            dispatch_fraction: f[i],
            reserve_share: r[i],
        })
        .collect();
    Dispatch { allocations, frequency_setpoint: fset }
}
RUST

cd "$DISPATCHER_DIR"
cargo build --release --offline --quiet
./target/release/dispatcher

python3 - << 'PY'
import sys
sys.path.insert(0, "/app/task_file/scripts")
from model import evaluate
r = evaluate("/app/task_file/input_data", "/app/task_file/output_data")
if "error" in r:
    print("ERROR:", r["error"]); sys.exit(1)

# Replicate the documented strict score so the reference plan proves it clears
# the quality gate, not just the raw score.
strict = r["total_score"] * 0.94
if r.get("freq_gap", 1.0) > 0.04:
    strict *= 0.50
if r.get("efficiency_score", 0.0) < 0.82:
    strict *= 0.55
if r.get("service_score", 0.0) < 0.92:
    strict *= 0.85
if r.get("renewable_fraction", 0.0) < 0.55:
    strict *= 0.90
if r.get("degraded_output", 0.0) > 800.0:
    strict *= 0.85
strict = round(max(0.0, min(1.0, strict)), 4)

print("solution self-check:", {k: r.get(k) for k in
      ("total_score","service_score","efficiency_score","stability_score",
       "freq_gap","renewable_fraction","total_emissions","committed_thermal")}, "strict:", strict)
import json
cfg = json.load(open("/app/task_file/input_data/config.json"))
if r.get("committed_thermal", 0) > cfg["max_committed_thermal"]:
    print(f"solution committed_thermal {r['committed_thermal']} exceeds cap"); sys.exit(1)
if r["total_score"] < 0.99:
    print(f"solution raw {r['total_score']} below 0.99"); sys.exit(1)
if strict < 0.92:
    print(f"solution strict {strict} below the binding 0.92 gate"); sys.exit(1)
PY
echo "Reference solution complete."
