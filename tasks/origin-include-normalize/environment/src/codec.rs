pub fn digest16(body: &str) -> String {
    let norm = body.split_whitespace().collect::<Vec<_>>().join(" ");
    let mut hash: u64 = 0xcbf29ce484222325;
    for b in norm.as_bytes() {
        hash ^= *b as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    format!("{:016x}", hash)
}

pub fn fold_label(name: &str, anchor: &str) -> String {
    let anchor = anchor.trim();
    if name.ends_with('.') {
        return name.to_lowercase();
    }
    if name == "@" {
        let base = anchor.trim_end_matches('.');
        return format!("{base}.");
    }
    let base = anchor.trim_end_matches('.');
    format!("{name}.{base}.")
}

pub fn build_body(holder: &str, rtype: &str, klass: &str, ttl: u64, rdata: &str) -> String {
    format!("{holder} {rtype} {klass} {ttl} {rdata}")
}

pub fn row_line(holder: &str, klass: &str, rtype: &str, ttl: u64, rdata: &str) -> String {
    format!("{holder} {ttl} {klass} {rtype} {rdata}")
}
