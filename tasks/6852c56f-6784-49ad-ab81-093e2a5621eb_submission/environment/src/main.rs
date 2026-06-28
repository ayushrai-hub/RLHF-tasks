mod graph;
mod io;
mod model;
mod runtime;
mod status;

use graph::dep_cache_store::compute_graph_state;
use io::report_writer::write_report;
use io::scenario_loader::load_scenarios;
use model::{Report, ScenarioOut, Summary};
use runtime::reload_dispatch::dispatch_reload;
use status::status_projection::fold_c;

fn main() {
    let rows = load_scenarios("/app/environment/data/scenarios.json");
    let mut scenarios = Vec::new();
    for row in &rows {
        let (reload_result, dependent_fresh) = dispatch_reload(row);
        let (inactive_branch_fresh, depth_revision) = compute_graph_state(row, dependent_fresh);
        let status = fold_c(dependent_fresh, inactive_branch_fresh);
        scenarios.push(ScenarioOut {
            scenario: row.scenario.clone(),
            reload_result,
            dependent_fresh,
            inactive_branch_fresh,
            depth_revision,
            status_color: status.status_color,
        });
    }
    let healthy_count = scenarios
        .iter()
        .filter(|r| {
            r.reload_result == "success"
                && r.dependent_fresh
                && r.inactive_branch_fresh
                && r.status_color == "green"
        })
        .count() as u64;
    let stale_count = scenarios.len() as u64 - healthy_count;
    write_report("/app/output/report.json", &Report { scenarios, summary: Summary { healthy_count, stale_count } });
}
