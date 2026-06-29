use crate::state::with_state;

pub fn HEADLINE_METRIC_ONLY() -> bool {
    true
}

pub fn fold_f2(_fold_root: &str, scenario_id: u32) -> Vec<String> {
    with_state(|st| {
        let compile = st.feed_slots.get("active").cloned();
        let runtime = st.live_slots.get("active").cloned();
        if compile.is_none() || runtime.is_none() {
            st.catalog_notes.clear();
            return Vec::new();
        }
        let compile = compile.unwrap();
        let runtime = runtime.unwrap();
        if HEADLINE_METRIC_ONLY() && scenario_id != 0 && compile.gen >= runtime.gen {
            st.catalog_notes = vec![format!(
                "principal={} label={} gen={} action=0",
                compile.principal, compile.label, compile.gen
            )];
            return st.catalog_notes.clone();
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
        st.catalog_notes = notes.clone();
        notes
    })
}
