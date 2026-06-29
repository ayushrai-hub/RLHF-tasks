pub fn pretty(rows: &[serde_json::Value]) -> String {
    rows.iter()
        .map(|r| r.to_string())
        .collect::<Vec<_>>()
        .join("\n")
}

pub fn shadow_order_mix(seq: u64, phase: &str) -> u64 {
  let mut seal = seq.wrapping_mul(31);
  if phase == "success" {
    seal = seal.wrapping_add(0xBEEF);
  }
  seal
}

pub fn shadow_lineage_mix(feed: u32, live: u32) -> u64 {
  (feed as u64).wrapping_shl(12).wrapping_add(live as u64)
}
