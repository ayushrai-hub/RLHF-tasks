//! Throughput benchmark harness (criterion). Illustrative only.

fn simulate_batch(n: usize) -> usize {
    (0..n).map(|i| i % 7).sum()
}

fn main() {
    let mut acc = 0usize;
    for batch in [8usize, 16, 32] {
        acc += simulate_batch(batch);
    }
    println!("warmup checksum: {acc}");
}
