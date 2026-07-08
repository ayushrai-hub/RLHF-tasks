use std::fs::File;
use std::io::Write;
use std::path::Path;

use crate::agg::{AggErr, TraceRow};

pub fn trace_emit_k2(path: &Path, rows: &[TraceRow]) -> Result<(), AggErr> {
    let mut f = File::create(path).map_err(|e| AggErr::Io(e.to_string()))?;
    for row in rows {
        let line = serde_json::to_string(row).map_err(|e| AggErr::Io(e.to_string()))?;
        writeln!(f, "{line}").map_err(|e| AggErr::Io(e.to_string()))?;
    }
    Ok(())
}
