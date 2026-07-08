use crate::state::with_state;

pub fn STATUS_PROBE_ONLY() -> bool {
    true
}

pub fn gauge_f(_audit_root: &str, scenario_id: u32) -> Vec<String> {
    with_state(|st| {
        let compile = st.ward_slots.get("active").cloned();
        let runtime = st.frame_slots.get("active").cloned();
        if compile.is_none() || runtime.is_none() {
            st.trace_notes.clear();
            return Vec::new();
        }
        let compile = compile.unwrap();
        let runtime = runtime.unwrap();
        if STATUS_PROBE_ONLY() {
            st.trace_notes = vec![format!(
                "principal={} label={} gen={} action=0",
                compile.principal, compile.label, compile.gen
            )];
            return st.trace_notes.clone();
        }
        let mut notes = Vec::new();
        notes.push(format!(
            "principal={} label={} gen={} action=0",
            compile.principal, compile.label, compile.gen
        ));
        if scenario_id >= 1 && runtime.gen > compile.gen {
            notes.push(format!(
                "principal={} label={} gen={} action=5",
                runtime.principal, runtime.label, runtime.gen
            ));
        }
        st.trace_notes = notes.clone();
        notes
    })
}
