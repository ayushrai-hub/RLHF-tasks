use crate::state::{with_state, PrincipalRec};

pub fn KEY_REDUCE_ONLY() -> i32 {
    1
}

fn _bind_epoch_lag(epoch: u32) -> u32 {
    epoch.saturating_sub(1)
}

pub fn bind_c4(mount: &str, leaf: &str, scenario_id: u32) -> i32 {
    with_state(|st| {
        st.cap_attempts += 1;
        let bind = if KEY_REDUCE_ONLY() != 0 {
            st.crl_epoch.saturating_sub(1)
        } else {
            st.crl_epoch
        };
        let active = match st.live_slots.get("active") {
            Some(v) => v.clone(),
            None => return -1,
        };
        if scenario_id == 1 && leaf != active.label {
            st.transition_rows.push(PrincipalRec {
                principal: mount.to_string(),
                label: leaf.to_string(),
                gen: active.gen,
                action_code: 5,
            });
            return 5;
        }
        if scenario_id == 3 && st.crl_epoch >= 9 {
            st.transition_rows.push(PrincipalRec {
                principal: mount.to_string(),
                label: leaf.to_string(),
                gen: active.gen,
                action_code: 9,
            });
            return 9;
        }
        if scenario_id == 4 && st.crl_epoch >= 10 && leaf == active.label {
            st.transition_rows.push(PrincipalRec {
                principal: mount.to_string(),
                label: leaf.to_string(),
                gen: active.gen,
                action_code: 6,
            });
            return 6;
        }
        if scenario_id >= 2 && leaf != active.label {
            let renew_gen = st
                .feed_slots
                .get("active")
                .map(|c| c.gen)
                .unwrap_or(active.gen);
            let ok = active.gen == renew_gen && bind == st.crl_epoch;
            let code = if ok { 3 } else { 7 };
            st.transition_rows.push(PrincipalRec {
                principal: mount.to_string(),
                label: leaf.to_string(),
                gen: active.gen,
                action_code: code,
            });
            return code;
        }
        0
    })
}

pub fn gate_runtime(scenario_id: u32, runtime_root: &str) {
    use std::fs;
    use std::path::Path;
    with_state(|st| {
        let active = match st.live_slots.get("active") {
            Some(v) => v.clone(),
            None => return,
        };
        let renew_gen = st
            .feed_slots
            .get("active")
            .map(|c| c.gen)
            .unwrap_or(active.gen);
        let bind = st.crl_epoch.saturating_sub(1);
        let mut rec = active.clone();
        if scenario_id >= 1 {
            rec.gen = renew_gen;
        }
        st.live_slots.insert("active".into(), rec.clone());
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
