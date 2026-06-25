//! Append-only patch cursor with direct and deferred probe paths.
pub mod clip;
pub mod codec;
pub mod diag;
pub mod gate;
pub mod path_txt;
pub mod pool;
pub mod ring;
pub mod session;
pub mod shell;
pub mod sidecar;
pub mod tools;
pub mod trace;
pub mod wire;

use crate::path_txt::read_seed_path;
use crate::sidecar::load::Root;
use std::io;

/// Emit a JSON document for the path given (bytes only; caller writes file).
pub fn emit_record(p: &str) -> io::Result<String> {
    let v = read_seed()?;
    let r: Root = serde_json::from_value(v)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    let d = std::path::Path::new(p)
        .parent()
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "out path has no parent"))?;
    let _ = std::fs::create_dir_all(d);
    let mut m = session::Driver::new(r);
    m.fill();
    m.render_json()
}

fn read_seed() -> io::Result<serde_json::Value> {
    read_seed_path(
        &std::env::var("TRACEFOLD_SEED")
            .unwrap_or_else(|_| "/app/data/seed/scenarios.json".to_string()),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pre_len() {
        assert!(!wire::PREAMBLE.is_empty());
    }
}

