use sha2::{Digest, Sha256};

use crate::model::{ShotResult, ShotSnapshot};

/// Decoy one-step publisher used by `simulate-shot` — bypasses staged snapshot file.
pub fn quick_export(snapshot: &ShotSnapshot) -> ShotResult {
    let mut sorted = snapshot.trace_ids.clone();
    sorted.sort_unstable();
    let body = sorted
        .iter()
        .map(|id| id.to_string())
        .collect::<Vec<_>>()
        .join(",");
    ShotResult {
        stack: snapshot.stack.clone(),
        seed: snapshot.seed,
        path_ledger_m: round6(snapshot.path_ledger_m),
        exit_energy_j: round3(snapshot.exit_energy_j),
        penetrated: snapshot.penetrated,
        layers: snapshot.layers.clone(),
        ricochet: snapshot.ricochet.clone(),
        trace_digest: hex_sha256(&body),
    }
}

fn hex_sha256(body: &str) -> String {
    Sha256::digest(body.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

fn round3(v: f64) -> f64 {
    (v * 1000.0).round() / 1000.0
}

fn round6(v: f64) -> f64 {
    (v * 1_000_000.0).round() / 1_000_000.0
}
