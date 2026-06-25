//! Small view helpers (non-gating).
pub fn head_char(s: &str) -> Option<char> {
    s.chars().next()
}

