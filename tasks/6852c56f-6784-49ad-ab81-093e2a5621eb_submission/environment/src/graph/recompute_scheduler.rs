pub fn schedule_recompute(seed: bool, fanout: u64) -> bool {
    seed && fanout > 0
}
