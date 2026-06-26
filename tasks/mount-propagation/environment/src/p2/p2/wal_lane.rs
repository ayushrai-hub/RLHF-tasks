use crate::n5::n5::rel_q::ObservationV;

pub fn obs_fingerprint(phase: &str, cycle: i32, note: &str) -> String {
    format!("{phase}:{cycle}:{note}")
}

pub fn collect_keys(obs: &[ObservationV]) -> Vec<String> {
    obs
        .iter()
        .map(|item| obs_fingerprint(&item.phase, item.cycle, &item.note))
        .collect()
}

pub fn replay_wal_tail(wal_keys: &[String], current: Vec<ObservationV>) -> Vec<ObservationV> {
    let mut out = Vec::new();
    for key in wal_keys {
        out.push(ObservationV {
            phase: "wal_replay".to_string(),
            cycle: 0,
            note: key.clone(),
            branch: String::new(),
        });
    }
    out.extend(current);
    out
}

pub fn wal_replay_count(obs: &[ObservationV]) -> usize {
    obs
        .iter()
        .filter(|item| item.phase == "wal_replay")
        .count()
}
