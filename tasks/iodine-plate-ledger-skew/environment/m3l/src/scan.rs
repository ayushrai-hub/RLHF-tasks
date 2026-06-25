use crate::cfg;
use crate::mix;
use serde::Deserialize;
use std::fs;
use std::path::Path;

#[derive(Debug, Deserialize)]
pub struct ScenarioMeta {
    pub scenario: String,
    pub segments: Vec<String>,
    pub profile: Option<String>,
    pub plate_lane: Option<u32>,
    pub prune_below: Option<u32>,
    pub rollback_after: Option<u32>,
    pub modulo_prune: Option<u32>,
}

pub fn load_meta(path: &Path) -> ScenarioMeta {
    let raw = fs::read_to_string(path).expect("read scenario");
    serde_json::from_str(&raw).expect("parse scenario")
}

#[derive(Debug, Clone)]
pub struct Row {
    pub name: String,
    pub seq: u32,
    pub plate_lane: u32,
    pub digest_ok: bool,
}

pub fn read_row(path: &Path, profile: &cfg::Profile) -> Row {
    let raw = fs::read(path).expect("read chunk");
    let name = path.file_name().unwrap().to_string_lossy().into_owned();
    if raw.len() < 24 || &raw[0..4] != b"PLT5" {
        return Row {
            name,
            seq: 0,
            plate_lane: 0,
            digest_ok: false,
        };
    }
    let plate_lane = u32::from(u16::from_be_bytes([raw[6], raw[7]]));
    let seq = u32::from_be_bytes([raw[12], raw[13], raw[14], raw[15]]);
    let len = u32::from_be_bytes([raw[16], raw[17], raw[18], raw[19]]) as usize;
    let end = 20usize.saturating_add(len);
    if raw.len() < end + 4 {
        return Row {
            name,
            seq: 0,
            plate_lane: 0,
            digest_ok: false,
        };
    }
    let span_start = cfg::digest_start(profile.digest_anchor);
    let digest_ok = mix::verify(&raw[span_start..end], &raw[end..end + 4]);
    Row {
        name,
        seq,
        plate_lane,
        digest_ok,
    }
}
