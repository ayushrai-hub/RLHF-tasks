use std::collections::BTreeMap;

use crate::config::{self, SiteConfig};
use crate::state::{LiveEvent, PersistedState};
use crate::window;

#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct DailyRow {
    pub date: String,
    pub hive_id: u16,
    pub weight_delta_kg: f64,
    pub samples: u32,
    pub first_event_id: u64,
    pub last_event_id: u64,
}

pub fn daily_rows(data: &PersistedState, cfg: &SiteConfig) -> Vec<DailyRow> {
    let mut buckets: BTreeMap<(String, u16), Vec<&LiveEvent>> = BTreeMap::new();
    for event in data.events.values() {
        if !event.live {
            continue;
        }
        let date = window::logical_date(event.timestamp, cfg);
        buckets
            .entry((date, event.canonical_hive_id))
            .or_default()
            .push(event);
    }

    let mut rows = Vec::new();
    for ((date, hive_id), mut events) in buckets {
        events.sort_by_key(|e| e.order);
        let samples = events.len() as u32;
        let delta = if samples < 2 {
            0.0
        } else {
            events.last().unwrap().net_kg - events.first().unwrap().net_kg
        };
        rows.push(DailyRow {
            date,
            hive_id,
            weight_delta_kg: config::round_field(delta, cfg.precision),
            samples,
            first_event_id: events.first().map(|e| e.event_id).unwrap_or(0),
            last_event_id: events.last().map(|e| e.event_id).unwrap_or(0),
        });
    }
    rows
}
