use serde::Deserialize;
use std::fs;

#[derive(Debug, Clone, Deserialize)]
pub struct TareEpoch {
    pub hive_id: u16,
    pub from_ts: u64,
    pub tare_kg: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CalibrationEpoch {
    pub hive_id: u16,
    pub from_ts: u64,
    pub scale: f64,
    pub offset_kg: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AliasEpoch {
    pub raw_hive_id: u16,
    pub canonical_hive_id: u16,
    pub from_ts: u64,
    pub until_ts: Option<u64>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SiteConfig {
    pub site_name: String,
    pub timezone_offset_minutes: i32,
    pub day_start_minutes: u32,
    #[serde(default = "default_precision")]
    pub precision: u32,
    #[serde(default)]
    pub tare_epoch: Vec<TareEpoch>,
    #[serde(default)]
    pub calibration_epoch: Vec<CalibrationEpoch>,
    #[serde(default)]
    pub alias_epoch: Vec<AliasEpoch>,
}

fn default_precision() -> u32 {
    3
}

pub fn load_config(path: &str) -> Result<SiteConfig, String> {
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    toml::from_str(&text).map_err(|e| e.to_string())
}

pub fn resolve_alias(raw_hive_id: u16, timestamp: u64, cfg: &SiteConfig) -> u16 {
    let mut best: Option<&AliasEpoch> = None;
    for alias in &cfg.alias_epoch {
        if alias.raw_hive_id != raw_hive_id || alias.from_ts > timestamp {
            continue;
        }
        if let Some(until) = alias.until_ts {
            if timestamp >= until {
                continue;
            }
        }
        if best.map(|b| alias.from_ts > b.from_ts).unwrap_or(true) {
            best = Some(alias);
        }
    }
    best.map(|b| b.canonical_hive_id).unwrap_or(raw_hive_id)
}

pub fn resolve_calibration(canonical_hive_id: u16, timestamp: u64, cfg: &SiteConfig) -> (f64, f64) {
    let mut scale = 1.0;
    let mut offset = 0.0;
    let mut best_ts = None;
    for epoch in &cfg.calibration_epoch {
        if epoch.hive_id != canonical_hive_id || epoch.from_ts > timestamp {
            continue;
        }
        if best_ts.map(|b| epoch.from_ts > b).unwrap_or(true) {
            best_ts = Some(epoch.from_ts);
            scale = epoch.scale;
            offset = epoch.offset_kg;
        }
    }
    (scale, offset)
}

pub fn resolve_tare(canonical_hive_id: u16, timestamp: u64, cfg: &SiteConfig) -> f64 {
    let mut tare = 0.0;
    let mut best_ts = None;
    for epoch in &cfg.tare_epoch {
        if epoch.hive_id != canonical_hive_id || epoch.from_ts > timestamp {
            continue;
        }
        if best_ts.map(|b| epoch.from_ts > b).unwrap_or(true) {
            best_ts = Some(epoch.from_ts);
            tare = epoch.tare_kg;
        }
    }
    tare
}

pub fn net_kg(raw_hive_id: u16, timestamp: u64, grams: i32, cfg: &SiteConfig) -> (u16, f64) {
    let canonical = resolve_alias(raw_hive_id, timestamp, cfg);
    let (scale, offset) = resolve_calibration(canonical, timestamp, cfg);
    let calibrated = (grams as f64 / 1000.0) * scale + offset;
    let tare = resolve_tare(canonical, timestamp, cfg);
    (canonical, calibrated - tare)
}

pub fn round_field(value: f64, precision: u32) -> f64 {
    let factor = 10_f64.powi(precision as i32);
    (value * factor).round() / factor
}
