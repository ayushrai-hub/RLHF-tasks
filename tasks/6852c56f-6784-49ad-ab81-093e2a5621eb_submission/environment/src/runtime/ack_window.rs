pub fn window_ready(u: &str, rev_hint: u64) -> bool {
    !u.is_empty() && rev_hint > 0
}
