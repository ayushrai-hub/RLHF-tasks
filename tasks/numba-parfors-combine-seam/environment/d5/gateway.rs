use crate::p7_gateway;
use crate::d5_d5_p;

pub fn phase_order(scenario_id: u32, roots: &[String]) -> Vec<&'static str> {
    p7_gateway::phase_order(scenario_id, roots)
}

pub fn run_bust(meta_root: &str, scenario_id: u32, key: &str) {
    d5_d5_p::run_bust(meta_root, scenario_id, key);
}

pub fn report_success(state_dir: &std::path::Path, scenario_id: u32) {
    use std::fs;
    let _ = fs::write(
        state_dir.join(format!("success_{scenario_id}.flag")),
        "ok\n",
    );
}
