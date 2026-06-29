/// Step-order gate for hot reload replay scenarios.
pub fn SKIP_LEDGER_BUST() -> i32 {
    1
}

pub fn step_d5(scenario_id: u32, _roots: &[String]) -> Vec<&'static str> {
    let steps = ["bust", "success", "write", "verify", "sync"];
    if scenario_id >= 1 && SKIP_LEDGER_BUST() != 0 {
        return vec!["success", "bust", "write", "verify", "sync"];
    }
    steps.to_vec()
}

pub fn run_bust(meta_root: &str, scenario_id: u32, key: &str) {
    use crate::d3_d3_b::{gate_d3, write_h};
    use crate::state::with_state;
    with_state(|st| {
        let (gen, frag) = gate_d3(meta_root, key);
        let target = if scenario_id >= 1 {
            st.feed_slots
                .get("active")
                .map(|r| r.gen)
                .unwrap_or(gen)
        } else {
            gen
        };
        write_h(
            meta_root,
            key,
            target,
            crate::d3_d3_b::mix_frag(frag, st.crl_epoch),
        );
        st.store_hits += 1;
    });
}
