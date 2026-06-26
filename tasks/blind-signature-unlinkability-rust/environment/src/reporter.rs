use crate::types::VerificationReport;
use std::fs;
use std::path::Path;

pub fn write_report(report: &VerificationReport, output_path: &Path) {
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent).ok();
    }
    let json_str = serde_json::to_string_pretty(report).expect("Failed to serialize");
    fs::write(output_path, json_str).expect("Failed to write output");
}
