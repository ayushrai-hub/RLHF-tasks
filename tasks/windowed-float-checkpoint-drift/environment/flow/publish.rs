use std::fs::File;
use std::io::Write;
use std::path::Path;

use crate::agg::{AggErr, DiffSummary, RunReport, TraceRow};
use crate::report::compare_h6::{diff_report_h6, diff_with_trace, TolBands};
use crate::report::trace_emit_k2::trace_emit_k2;

pub fn write_run_report(path: &Path, report: &RunReport) -> Result<(), AggErr> {
    let data = serde_json::to_vec_pretty(report).map_err(|e| AggErr::Io(e.to_string()))?;
    let mut f = File::create(path).map_err(|e| AggErr::Io(e.to_string()))?;
    f.write_all(&data).map_err(|e| AggErr::Io(e.to_string()))
}

pub fn write_diff_summary(path: &Path, summary: &DiffSummary) -> Result<(), AggErr> {
    let data = serde_json::to_vec_pretty(summary).map_err(|e| AggErr::Io(e.to_string()))?;
    let mut f = File::create(path).map_err(|e| AggErr::Io(e.to_string()))?;
    f.write_all(&data).map_err(|e| AggErr::Io(e.to_string()))
}

pub fn build_diff(
    cold: &RunReport,
    warm: &RunReport,
    trace: &[TraceRow],
    seal_gen: u64,
    drain_wm: u64,
) -> Result<DiffSummary, AggErr> {
    let tol = TolBands::default();
    diff_with_trace(cold, warm, &tol, trace, seal_gen, drain_wm)
}

pub fn build_diff_simple(cold: &RunReport, warm: &RunReport) -> Result<DiffSummary, AggErr> {
    diff_report_h6(cold, warm, &TolBands::default())
}

pub fn emit_trace(path: &Path, trace: &[TraceRow]) -> Result<(), AggErr> {
    trace_emit_k2(path, trace)
}
