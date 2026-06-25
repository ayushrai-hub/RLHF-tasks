use std::fs;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Profile {
    pub digest_anchor: u8,
    pub lane_mask: u32,
}

impl Default for Profile {
    fn default() -> Self {
        Self {
            digest_anchor: 0,
            lane_mask: 0xFFFF,
        }
    }
}

fn parse_u32(raw: &str, key: &str) -> Option<u32> {
    for line in raw.lines() {
        let line = line.split('#').next().unwrap_or("").trim();
        if let Some((k, v)) = line.split_once('=') {
            if k.trim() == key {
                return v.trim().parse().ok();
            }
        }
    }
    None
}

pub fn load(name: &str) -> Profile {
    let path = Path::new("/app/profiles").join(format!("{name}.toml"));
    let raw = fs::read_to_string(&path).unwrap_or_default();
    let mut profile = Profile::default();
    if let Some(v) = parse_u32(&raw, "digest_anchor") {
        profile.digest_anchor = v as u8;
    }
    if let Some(v) = parse_u32(&raw, "lane_mask") {
        profile.lane_mask = v;
    }
    profile
}

pub fn digest_start(anchor: u8) -> usize {
    if anchor == 1 { 6 } else { 8 }
}

pub fn default_profile() -> Profile {
    Profile::default()
}
