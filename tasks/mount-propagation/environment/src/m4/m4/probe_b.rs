use std::collections::HashMap;

pub fn probe_summary(stamps: &HashMap<String, String>) -> String {
    let mut keys: Vec<&String> = stamps.keys().collect();
    keys.sort();
    keys.into_iter()
        .map(|k| format!("{k}:{}", stamps[k]))
        .collect::<Vec<_>>()
        .join(";")
}
