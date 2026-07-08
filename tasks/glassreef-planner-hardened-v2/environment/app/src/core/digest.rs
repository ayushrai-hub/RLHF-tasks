pub fn fnv1a64_hex(text: &str) -> String {
    let mut hash: u64 = 14695981039346656037;
    for b in text.as_bytes() {
        hash ^= *b as u64;
        hash = hash.wrapping_mul(1099511628211);
    }
    format!("{:016x}", hash)
}
