use crate::sim::flows::{route_subset, route_z, BranchRecord, RunRecord};
use crate::sim::case::bundled_scenarios;

fn quote(text: &str) -> String {
    let escaped = text.replace('\\', "\\\\").replace('"', "\\\"");
    format!("\"{}\"", escaped)
}

fn branch_json(branch: &BranchRecord) -> String {
    let entries = branch
        .entries
        .iter()
        .map(|line| quote(line))
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "{{\"branch\":{},\"aggregate_digest\":{},\"event_digest\":{},\"seq_high_water\":{},\"checkpoint_bytes\":{},\"fold_records\":{},\"entries\":[{}]}}",
        quote(&branch.branch),
        quote(&branch.aggregate_digest),
        quote(&branch.event_digest),
        branch.seq_high_water,
        branch.checkpoint_bytes,
        branch.fold_records,
        entries
    )
}

fn run_json(run: &RunRecord) -> String {
    let branches = run
        .branches
        .iter()
        .map(branch_json)
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "{{\"scenario\":{},\"seq_high_water\":{},\"branches\":[{}]}}",
        quote(&run.scenario),
        run.seq_high_water,
        branches
    )
}

pub fn render_report() -> String {
    let runs = bundled_scenarios().iter().map(route_z).collect::<Vec<_>>();
    render_runs(&runs)
}

pub fn render_report_subset(names: &[&str]) -> String {
    let runs = route_subset(names);
    render_runs(&runs)
}

fn render_runs(runs: &[RunRecord]) -> String {
    let body = runs.iter().map(run_json).collect::<Vec<_>>().join(",");
    format!("{{\"report_version\":1,\"runs\":[{}]}}\n", body)
}
