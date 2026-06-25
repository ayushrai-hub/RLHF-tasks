pub const CURSOR_SEED: u64 = 0x510e527fade682d1;
pub const TOMBSTONE_TAG: u64 = 0x9b05688c2b3e6c1f;

pub fn align4(n: usize) -> usize {
    (n + 3) & !3
}

pub fn apply_delta(value: u64, delta: u64, revision: u32) -> u64 {
    value.wrapping_add(delta.rotate_left(revision % 31))
}

pub fn apply_flags(flags: u32, toggle_mask: u32, seq: u64) -> u32 {
    flags ^ toggle_mask.rotate_left(((seq & 31) as u32).wrapping_add(1))
}

pub fn cursor_fold(
    acc: u64,
    seq: u64,
    revision: u32,
    delta: u64,
    toggle_mask: u32,
) -> u64 {
    (acc
        ^ seq.rotate_left(revision & 31)
        ^ delta.rotate_right((seq & 31) as u32)
        ^ (toggle_mask as u64).rotate_left(22))
    .rotate_left(17)
    .wrapping_mul(0x9e37_79b1_85eb_ca87)
}

pub fn cursor_fold_winner(
    acc: u64,
    seq: u64,
    revision: u32,
    patch_id: u64,
    delta: u64,
    toggle_mask: u32,
    tombstone: bool,
) -> u64 {
    let tagged = acc
        ^ patch_id.rotate_left(11)
        ^ if tombstone { TOMBSTONE_TAG } else { 0 };
    cursor_fold(tagged, seq, revision, delta, toggle_mask)
}

pub fn probe_matches(
    value: u64,
    flags: u32,
    modulus: u64,
    remainder: u64,
    required_flags: u32,
) -> bool {
    modulus != 0
        && value % modulus == remainder
        && flags & required_flags == required_flags
}

