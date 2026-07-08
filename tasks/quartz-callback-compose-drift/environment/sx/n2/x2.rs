/// Build a stable digest string over case outputs.
pub fn bundle_digest(rows: &[(String, i32, f64)]) -> String {
    rows.iter()
        .map(|(tag, event_step, _metric)| format!("{}:{}", tag, event_step))
        .collect::<Vec<_>>()
        .join("|")
}
