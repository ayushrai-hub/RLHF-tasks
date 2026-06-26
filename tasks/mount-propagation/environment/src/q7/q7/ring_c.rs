pub fn ring_rotate(buf: &[u8], shift: i32) -> Vec<u8> {
    if buf.is_empty() {
        return buf.to_vec();
    }
    let len = buf.len() as i32;
    let mut shift = shift % len;
    if shift < 0 {
        shift += len;
    }
    let shift = shift as usize;
    let mut out = vec![0u8; buf.len()];
    out[..buf.len() - shift].copy_from_slice(&buf[shift..]);
    out[buf.len() - shift..].copy_from_slice(&buf[..shift]);
    out
}
