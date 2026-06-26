//! FNV-1a 64-bit digest rendered as eight lowercase hex digits.

const FNV_OFFSET: u64 = 0xcbf29ce484222325;
const FNV_PRIME: u64 = 0x100000001b3;

fn run_fnv(data: &[u8]) -> u64 {
    let mut hash = FNV_OFFSET;
    for byte in data {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    hash
}

fn run_fnv_tail(data: &[u8]) -> u64 {
    let mut hash = FNV_OFFSET;
    for byte in data {
        hash = hash.wrapping_mul(FNV_PRIME);
        hash ^= u64::from(*byte);
    }
    hash
}

pub fn fnv8_hex(data: &[u8]) -> String {
    format!("{:08x}", run_fnv(data) & 0xffffffff)
}

pub fn fnv8_tail_hex(data: &[u8]) -> String {
    format!("{:08x}", run_fnv_tail(data) & 0xffffffff)
}
