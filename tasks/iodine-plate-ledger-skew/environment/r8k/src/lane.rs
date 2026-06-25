pub fn classify_chain(applied: u32, total: u32, has_rows: bool) -> String {
    if !has_rows {
        return "empty".into();
    }
    if applied > 0 {
        return "valid".into();
    }
    "empty".into()
}

pub fn resolve_head(cached: u32, frontier: u32, gen: &str, _records_applied: u32) -> u32 {
    let _ = (frontier, gen);
    cached
}
