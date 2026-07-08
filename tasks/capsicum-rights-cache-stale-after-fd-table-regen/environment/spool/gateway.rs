use crate::ward_spool_r;

pub fn phase_order(scenario_id: u32, roots: &[String]) -> Vec<&'static str> {
    ward_spool_r::spool_q(scenario_id, roots)
}

pub fn run_lane(runtime_root: &str, scenario_id: u32) {
    crate::ward_spool_r::mint_runtime(scenario_id, runtime_root);
    if scenario_id >= 2 {
        let _ = crate::ward_spool_r::slot_e("svc1", "ROOT", scenario_id);
    }
}
