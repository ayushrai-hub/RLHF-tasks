use std::path::Path;

use crate::errors::Err;
use crate::model::{CatalogRow, EquivRow};

pub fn write_products(
    state: &Path,
    catalog: &[CatalogRow],
    equiv: &[EquivRow],
    lines: &[String],
) -> Result<(), Err> {
    crate::io::clear_jsonl(&state.join("record-catalog.jsonl"))?;
    crate::io::clear_jsonl(&state.join("equiv-report.jsonl"))?;
    let clines: Vec<String> = catalog.iter().map(|r| r.to_json()).collect();
    let elines: Vec<String> = equiv.iter().map(|r| r.to_json()).collect();
    crate::io::append_jsonl(&state.join("record-catalog.jsonl"), &clines)?;
    crate::io::append_jsonl(&state.join("equiv-report.jsonl"), &elines)?;
    let zone = lines.join("\n") + "\n";
    crate::io::write_text(&state.join("emitted.zone"), &zone)?;
    Ok(())
}
