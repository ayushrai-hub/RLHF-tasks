use std::collections::HashMap;

fn stamp_class(key: &str) -> u8 {
    if key.ends_with("_mk") {
        1
    } else if key.ends_with("_rk") {
        2
    } else {
        0
    }
}

pub fn wave_targets<'a>(keys: impl Iterator<Item = &'a String>, pass: i32) -> Vec<String> {
    if pass < 2 {
        return Vec::new();
    }
    keys.filter(|key| stamp_class(key) != 2)
        .map(|key| key.clone())
        .collect()
}

pub fn apply_wave(stamps: HashMap<String, String>, pass: i32) -> HashMap<String, String> {
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

pub fn ring_rotate(buf: &[u8], shift: i32) -> Vec<u8> {
    if buf.is_empty() {
        return buf.to_vec();
    }
    let len = buf.len() as i32;
    let mut shift = shift % len;
    if shift < 0 {
        shift += len;
    }
    let shift = shift as usize;
    let mut out = vec![0u8; buf.len()];
    out[..buf.len() - shift].copy_from_slice(&buf[shift..]);
    out[buf.len() - shift..].copy_from_slice(&buf[..shift]);
    out
}
