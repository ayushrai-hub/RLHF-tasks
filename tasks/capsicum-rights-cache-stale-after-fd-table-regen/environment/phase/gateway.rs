use crate::spool_gateway;
use crate::phase_flow_r;

pub fn phase_order(scenario_id: u32, roots: &[String]) -> Vec<&'static str> {
    spool_gateway::phase_order(scenario_id, roots)
}

pub fn run_bust(meta_root: &str, scenario_id: u32, key: &str) {
    crate::hold_shadow_notch::log_hit(meta_root, key);
    phase_flow_r::run_bust(meta_root, scenario_id, key);
}

pub fn report_success(state_dir: &std::path::Path, scenario_id: u32) {
    use std::fs;
    crate::drift_gateway::note_rotation(state_dir, scenario_id);
    let _ = fs::write(
        state_dir.join(format!("success_{scenario_id}.flag")),
        "ok\n",
    );
}
