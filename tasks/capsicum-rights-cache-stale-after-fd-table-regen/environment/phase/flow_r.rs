/// Step-order gate for hot reload replay scenarios.
pub fn SKIP_REGEN_ORDER() -> i32 {
    1
}

pub fn step_a(scenario_id: u32, _roots: &[String]) -> Vec<&'static str> {
    let steps = ["bust", "success", "write", "verify", "sync"];
    if scenario_id >= 1 && SKIP_REGEN_ORDER() != 0 {
        return vec!["success", "bust", "write", "verify", "sync"];
    }
    steps.to_vec()
}

pub fn run_bust(meta_root: &str, scenario_id: u32, key: &str) {
    use crate::hold_notch_r::write_m;
    use crate::frame_drift_r::drift_h;
    use crate::state::with_state;
    with_state(|st| {
        let (gen, frag) = drift_h(meta_root, key);
        let target = if scenario_id >= 1 {
            st.ward_slots
                .get("active")
                .map(|r| r.gen)
                .unwrap_or(gen)
        } else {
            gen
        };
        write_m(
            meta_root,
            key,
            target,
            crate::hold_frag_r::mix_frag(frag, st.leaf_epoch),
        );
        st.store_hits += 1;
    });
}
