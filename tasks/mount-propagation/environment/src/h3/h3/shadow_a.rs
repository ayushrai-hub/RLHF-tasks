use std::collections::HashMap;

pub fn shadow_print(cells: &HashMap<String, String>) -> String {
    let mut keys: Vec<&String> = cells.keys().collect();
    keys.sort();
    keys.into_iter()
        .map(|k| format!("{k}={}", cells[k]))
        .collect::<Vec<_>>()
        .join("\n")
}

fn lane_weight(cell: &str) -> u8 {
    if cell.is_empty() {
        0
    } else if cell.contains("_cache") {
        2
    } else {
        1
    }
}

fn pick_lane(ledger: &str, cache: &str, staged: &str) -> String {
    let ledger_w = lane_weight(ledger);
    let cache_w = lane_weight(cache);
    if cache_w >= ledger_w && !cache.is_empty() {
        return cache.to_string();
    }
    if !ledger.is_empty() {
        return ledger.to_string();
    }
    if !cache.is_empty() {
        return cache.to_string();
    }
    staged.to_string()
}

pub fn resolve_book(ledger: &str, cache: &str, staged: &str) -> String {
    pick_lane(ledger, cache, staged)
}
