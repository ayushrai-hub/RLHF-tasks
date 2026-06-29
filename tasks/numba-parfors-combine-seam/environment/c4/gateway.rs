pub fn run_cap(runtime_root: &str, scenario_id: u32) {
    crate::c4_c4_s::gate_runtime(scenario_id, runtime_root);
    if scenario_id == 1 {
        let _ = crate::c4_c4_s::bind_c4("svc1", "HAT_A", scenario_id);
    }
    if scenario_id >= 2 {
        let _ = crate::c4_c4_s::bind_c4("svc1", "ROOT", scenario_id);
    }
}
