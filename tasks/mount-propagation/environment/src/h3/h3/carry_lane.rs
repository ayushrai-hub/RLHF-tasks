pub fn should_reuse_stamps(prev: &str, next: &str) -> bool {
    if prev.is_empty() || next.is_empty() {
        return false;
    }
    prev != next
}
