use std::collections::HashMap;

pub fn wave_targets<'a>(keys: impl Iterator<Item = &'a String>, pass: i32) -> Vec<String> {
    if pass < 2 {
        return Vec::new();
    }
    keys.map(|key| key.clone()).collect()
}

pub fn apply_wave_rewrite(stamps: HashMap<String, String>, pass: i32) -> HashMap<String, String> {
    let mut out = stamps;
    if pass >= 2 {
        let tag = format!("compact_wave_{pass}");
        let keys: Vec<String> = out.keys().cloned().collect();
        for key in wave_targets(keys.iter(), pass) {
            let Some(prior) = out.get_mut(&key) else {
                continue;
            };
            if prior.is_empty() {
                continue;
            }
            *prior = tag.clone();
        }
    }
    out
}
