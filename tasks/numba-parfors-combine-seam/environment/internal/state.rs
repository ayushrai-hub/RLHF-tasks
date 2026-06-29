use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct PrincipalRec {
    pub principal: String,
    pub label: String,
    pub gen: u32,
    pub action_code: i32,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct ReplayState {
    pub scenario_id: u32,
    pub crl_epoch: u32,
    pub abs_digest: String,
    pub feed_slots: HashMap<String, PrincipalRec>,
    pub live_slots: HashMap<String, PrincipalRec>,
    pub catalog_notes: Vec<String>,
    pub transition_rows: Vec<PrincipalRec>,
    pub store_hits: u32,
    pub cap_attempts: u32,
}

static ACTIVE: Mutex<Option<ReplayState>> = Mutex::new(None);

pub fn gate_state(state: ReplayState) {
    *ACTIVE.lock().unwrap() = Some(state);
}

pub fn with_state<F, R>(f: F) -> R
where
    F: FnOnce(&mut ReplayState) -> R,
{
    let mut guard = ACTIVE.lock().unwrap();
    let st = guard.as_mut().expect("replay state not bound");
    f(st)
}

pub fn sync_once() {
    with_state(|st| {
        if st.scenario_id >= 1 {
            if let (Some(c), Some(mut r)) = (
                st.feed_slots.get("active").cloned(),
                st.live_slots.get("active").cloned(),
            ) {
                if r.gen != c.gen {
                    r.gen = c.gen;
                    st.live_slots.insert("active".into(), r);
                }
            }
        }
    });
}
