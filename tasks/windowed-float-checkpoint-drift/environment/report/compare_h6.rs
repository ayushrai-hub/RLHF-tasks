use crate::agg::{DiffSummary, MetricDelta, RunReport, TraceRow};

pub struct TolBands {
    pub mean_abs: f64,
    pub moment_rel: f64,
    pub quant_abs: f64,
}

impl Default for TolBands {
    fn default() -> Self {
        Self {
            mean_abs: 1e-12,
            moment_rel: 1e-9,
            quant_abs: 1e-8,
        }
    }
}

fn within(name: &str, cold: f64, warm: f64, tol: &TolBands) -> bool {
    let abs_d = (cold - warm).abs();
    match name {
        "count" | "sum" => cold == warm,
        "mean" => abs_d <= tol.mean_abs,
        "stddev" | "var" => {
            let denom = cold.abs().max(1e-15);
            abs_d / denom <= tol.moment_rel
        }
        "p50" | "p95" | "p99" => abs_d <= tol.quant_abs,
        _ => abs_d <= tol.mean_abs,
    }
}

pub fn diff_report_h6(
    cold: &RunReport,
    warm: &RunReport,
    tol: &TolBands,
) -> Result<DiffSummary, crate::agg::AggErr> {
    let mut metric_deltas = Vec::new();
    for (name, ccell) in &cold.metrics {
        let wcell = warm
            .metrics
            .get(name)
            .ok_or_else(|| crate::agg::AggErr::Parse(format!("missing metric {name}")))?;
        let cold_v = ccell.value;
        let warm_v = wcell.value;
        let abs_delta = (cold_v - warm_v).abs();
        let rel_delta = if cold_v.abs() > 1e-15 {
            abs_delta / cold_v.abs()
        } else {
            abs_delta
        };
        metric_deltas.push(MetricDelta {
            name: name.clone(),
            cold: cold_v,
            warm: warm_v,
            abs_delta,
            rel_delta,
            within_band: within(name, cold_v, warm_v, tol),
        });
    }
    Ok(DiffSummary {
        metric_deltas,
        ordering_violations: 0,
        max_combine_rank: 0,
        frame_gen: warm.frame_gen,
        seal_gen: 0,
        drain_wm: 0,
        plan_digest: warm.plan_digest.clone(),
    })
}

pub fn diff_with_trace(
    cold: &RunReport,
    warm: &RunReport,
    tol: &TolBands,
    trace: &[TraceRow],
    seal_gen: u64,
    drain_wm: u64,
) -> Result<DiffSummary, crate::agg::AggErr> {
    let mut summary = diff_report_h6(cold, warm, tol)?;
    let mut prev = 0u64;
    let mut violations = 0u64;
    let mut max_rank = 0u64;
    for row in trace {
        if row.combine_rank < prev {
            violations += 1;
        }
        prev = row.combine_rank;
        max_rank = max_rank.max(row.combine_rank);
    }
    summary.ordering_violations = violations;
    summary.max_combine_rank = max_rank;
    summary.seal_gen = seal_gen;
    summary.drain_wm = drain_wm;
    Ok(summary)
}
