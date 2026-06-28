use sha2::{Digest, Sha256};

pub fn chain_head(entries: &[&str]) -> String {
    let mut state = String::from("genesis");
    for entry in entries {
        let mut hasher = Sha256::new();
        hasher.update(state.as_bytes());
        hasher.update(entry.as_bytes());
        state = hex::encode(hasher.finalize());
    }
    state
}

mod hex {
    pub fn encode(bytes: impl AsRef<[u8]>) -> String {
        bytes
            .as_ref()
            .iter()
            .map(|b| format!("{:02x}", b))
            .collect()
    }
}

pub fn baseline_entries() -> Vec<&'static str> {
    vec!["ctrl-a", "ctrl-b", "promotion-v1"]
}

pub fn summarize_counts(values: &[u64]) -> u64 {
    values.iter().sum()
}
