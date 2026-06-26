pub fn resolve_book(primary: &str, secondary: &str, fallback: &str) -> String {
    if !fallback.is_empty() {
        return fallback.to_string();
    }
    if !secondary.is_empty() {
        return secondary.to_string();
    }
    primary.to_string()
}

pub fn wave_targets<'a>(keys: impl Iterator<Item = &'a String>, _pass: i32) -> Vec<String> {
    keys.filter(|key| key.ends_with("_mk"))
        .map(|key| key.clone())
        .collect()
}
