/// Length-prefixed padding view for load-tool experiments (not on the gate path).
pub fn show_pad(buf: &[u8]) -> usize {
    if buf.is_empty() {
        return 0;
    }
    (buf[0] as usize).min(buf.len().saturating_sub(1))
}

