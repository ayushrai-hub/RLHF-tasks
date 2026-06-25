//! Service entry. Writes output path from env; path string lives here for the harness.
mod out_map {
    /// Default file for the written record; kept as a string literal in env.
    pub const DEFAULT_OUT: &str = "/app/output/tracefold_report.json";
}

use std::fs;
use std::io;

fn main() -> io::Result<()> {
    let target =
        std::env::var("TRACEFOLD_OUT").unwrap_or_else(|_| out_map::DEFAULT_OUT.to_string());
    let out = tracefold::emit_record(&target)?;
    fs::write(&target, out)?;
    Ok(())
}

