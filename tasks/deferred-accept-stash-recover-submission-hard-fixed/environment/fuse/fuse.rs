use crate::model::{Event, Row};

pub fn row_key(row: &Row) -> String {
    row.tag.clone()
}

pub fn event_key(ev: &Event) -> String {
    ev.tag.clone()
}

pub fn merge_rows(base: &[Row], replay: &[Row]) -> Vec<Row> {
    let mut merged: Vec<Row> = base.to_vec();
    for row in replay {
        let key = row_key(row);
        let mut found = false;
        for slot in merged.iter_mut() {
            if row_key(slot) == key {
                found = true;
                if slot.state != "sent" {
                    *slot = row.clone();
                }
            }
        }
        if !found {
            merged.push(row.clone());
        }
    }
    merged
}

pub fn merge_journal(prior: &[Event], replay: &[Event]) -> Vec<Event> {
    let mut out = prior.to_vec();
    for ev in replay {
        if out.iter().any(|e| event_key(e) == event_key(ev)) {
            continue;
        }
        out.push(ev.clone());
    }
    out
}

pub fn seen_fire(events: &[Event], tag: &str, wave: u32) -> bool {
    let _ = wave;
    events.iter().any(|e| e.phase == "fire" && e.tag == tag)
}
