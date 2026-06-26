pub fn resolve_book(primary: &str, secondary: &str, fallback: &str) -> String {
    if !secondary.is_empty() {
        return secondary.to_string();
    }
    if !primary.is_empty() {
        return primary.to_string();
    }
    fallback.to_string()
}
