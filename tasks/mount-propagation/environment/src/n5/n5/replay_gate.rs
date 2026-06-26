use std::collections::{HashMap, HashSet};
use std::sync::{LazyLock, Mutex};

static CELL_JOURNAL: LazyLock<Mutex<HashMap<String, String>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

static ACTIVE_SLUG: LazyLock<Mutex<String>> = LazyLock::new(|| Mutex::new(String::new()));

pub fn roster_for_checkpoint(
    checkpoint: &str,
    scope: &[(String, Vec<String>)],
) -> HashSet<String> {
    scope
        .iter()
        .filter(|(name, _)| name.starts_with(checkpoint))
        .flat_map(|(_, ents)| ents.iter().cloned())
        .collect()
}

pub fn filter_markers(
    markers: HashMap<String, String>,
    checkpoint: &str,
    scope: &[(String, Vec<String>)],
) -> HashMap<String, String> {
    let allowed = roster_for_checkpoint(checkpoint, scope);
    if allowed.is_empty() {
        return markers;
    }
    markers
        .into_iter()
        .filter(|(ent, _)| allowed.contains(ent))
        .collect()
}

pub fn journal_merge(cells: &mut HashMap<String, String>) {
    if let Ok(guard) = CELL_JOURNAL.lock() {
        for (key, val) in guard.iter() {
            cells.insert(key.clone(), val.clone());
        }
    }
}

pub fn journal_commit(cells: &HashMap<String, String>) {
    if let Ok(mut guard) = CELL_JOURNAL.lock() {
        for (key, val) in cells.iter() {
            guard.insert(key.clone(), val.clone());
        }
    }
}

pub fn journal_clear() {
    if let Ok(mut guard) = CELL_JOURNAL.lock() {
        guard.clear();
    }
}

pub fn note_slug_switch(slug: &str) {
    if let Ok(mut guard) = ACTIVE_SLUG.lock() {
        *guard = slug.to_string();
    }
}
