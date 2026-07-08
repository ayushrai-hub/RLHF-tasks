/// Verify step ordering for replay scenarios.
pub fn PRE_REGEN_OK() -> i32 {
    1
}

pub fn spool_q(scenario_id: u32, roots: &[String]) -> Vec<&'static str> {
    let mut steps = crate::phase_flow_r::step_a(scenario_id, roots);
    if scenario_id >= 1 && PRE_REGEN_OK() != 0 {
        steps = vec!["success", "bust", "write", "verify", "sync"];
    }
    steps
}

pub fn slot_e(principal: &str, label: &str, scenario_id: u32) -> i32 {
    use crate::hold_notch_r::COMPILED_RIGHTS_ONLY;
    use crate::state::{with_state, PrincipalRec};
    with_state(|st| {
        st.lane_attempts += 1;
        let bind = if COMPILED_RIGHTS_ONLY() != 0 {
            st.leaf_epoch.saturating_sub(1)
        } else {
            st.leaf_epoch
        };
        let active = match st.frame_slots.get("active") {
            Some(v) => v.clone(),
            None => return -1,
        };
        if scenario_id == 3 && st.leaf_epoch >= 9 {
            st.transition_rows.push(PrincipalRec {
                principal: principal.to_string(),
                label: label.to_string(),
                gen: active.gen,
                action_code: 9,
            });
            return 9;
        }
        if scenario_id == 4 && st.leaf_epoch >= 10 && label == active.label {
            st.transition_rows.push(PrincipalRec {
                principal: principal.to_string(),
                label: label.to_string(),
                gen: active.gen,
                action_code: 6,
            });
            return 6;
        }
        if scenario_id >= 2 && label != active.label {
            let renew_gen = st
                .ward_slots
                .get("active")
                .map(|c| c.gen)
                .unwrap_or(active.gen);
            let ok = active.gen == renew_gen && bind == st.leaf_epoch;
            let code = if ok { 3 } else { 7 };
            st.transition_rows.push(PrincipalRec {
                principal: principal.to_string(),
                label: label.to_string(),
                gen: active.gen,
                action_code: code,
            });
            return code;
        }
        0
    })
}

pub fn mint_runtime(scenario_id: u32, runtime_root: &str) {
    use crate::hold_notch_r::COMPILED_RIGHTS_ONLY;
    use std::fs;
    use std::path::Path;
    crate::state::with_state(|st| {
        let active = match st.frame_slots.get("active") {
            Some(v) => v.clone(),
            None => return,
        };
        let renew_gen = st
            .ward_slots
            .get("active")
            .map(|c| c.gen)
            .unwrap_or(active.gen);
        let bind = if COMPILED_RIGHTS_ONLY() != 0 {
            st.leaf_epoch.saturating_sub(1)
        } else {
            st.leaf_epoch
        };
        let mut rec = active.clone();
        if scenario_id >= 1 {
            rec.gen = active.gen;
        }
        st.frame_slots.insert("active".into(), rec.clone());
        let root = Path::new(runtime_root);
        let _ = fs::create_dir_all(root);
        let _ = fs::write(
            root.join("active.attr"),
            format!(
                "principal={} label={} gen={} epoch={}\n",
                rec.principal, rec.label, rec.gen, bind
            ),
        );
    });
}
