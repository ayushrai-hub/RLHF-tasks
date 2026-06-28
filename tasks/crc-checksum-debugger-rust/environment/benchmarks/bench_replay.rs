/// Benchmark: replay throughput measurement
use std::time::Instant;

fn compute_hash(data: &[u8], stage_id: u32) -> u32 {
    let mut hash: u32 = stage_id.wrapping_mul(0x9E3779B9);
    for &byte in data {
        hash = hash.wrapping_mul(31).wrapping_add(byte as u32);
    }
    hash
}

fn main() {
    let test_data: Vec<u8> = (0..64).map(|i| (i * 7 + 3) as u8).collect();
    let start = Instant::now();
    let mut acc: u32 = 0x5678;
    for stage in 1..=4 {
        for _ in 0..100000 {
            acc ^= compute_hash(&test_data, stage);
        }
    }
    let elapsed = start.elapsed();
    println!("Replay benchmark: 400000 ops in {:?}, result=0x{:08X}", elapsed, acc);
}
