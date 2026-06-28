pub fn digest_slice(name: &str, fanout: u64) -> String {
    format!("{name}:{fanout}")
}
