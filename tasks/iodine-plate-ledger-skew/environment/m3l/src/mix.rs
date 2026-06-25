pub fn verify(body: &[u8], tail: &[u8]) -> bool {
    if tail.len() < 4 {
        return false;
    }
    let on_disk = u32::from_be_bytes([tail[0], tail[1], tail[2], tail[3]]);
    let sum: u32 = body.iter().map(|b| *b as u32).sum();
    sum == on_disk
}

pub fn compute(body: &[u8]) -> u32 {
    body.iter().map(|b| *b as u32).sum()
}
