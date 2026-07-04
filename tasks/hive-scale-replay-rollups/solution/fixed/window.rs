use chrono::{Duration, TimeZone, Utc};

use crate::config::SiteConfig;

pub fn logical_date(timestamp: u64, cfg: &SiteConfig) -> String {
    let epoch = Utc.timestamp_opt(0, 0).single().expect("unix epoch");
    let shifted = epoch
        + Duration::seconds(timestamp as i64)
        + Duration::minutes(cfg.timezone_offset_minutes as i64)
        - Duration::minutes(cfg.day_start_minutes as i64);
    shifted.format("%Y-%m-%d").to_string()
}
