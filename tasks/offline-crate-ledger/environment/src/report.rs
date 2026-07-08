use std::fs;
use std::path::Path;

use crate::lock::esc;
use crate::model::Conflict;

pub fn conflict_report(conflicts: &[Conflict]) -> String {
    let mut sorted_conflicts = conflicts.to_vec();
    sorted_conflicts.sort_by(|a, b| a.package.cmp(&b.package));
    let mut out = String::from("{\n  \"conflicts\": [");
    if !sorted_conflicts.is_empty() {
        out.push('\n');
        for (cidx, conflict) in sorted_conflicts.iter().enumerate() {
            if cidx > 0 {
                out.push_str(",\n");
            }
            let mut sorted = conflict.constraints.clone();
            sorted.sort();
            out.push_str("    {\n");
            out.push_str(&format!(
                "      \"package\": \"{}\",\n",
                esc(&conflict.package)
            ));
            out.push_str("      \"constraints\": [");
            for (idx, constraint) in sorted.iter().enumerate() {
                if idx > 0 {
                    out.push_str(", ");
                }
                out.push_str(&format!("\"{}\"", esc(constraint)));
            }
            out.push_str("],\n");
            out.push_str(&format!(
                "      \"reason\": \"{}\"\n",
                esc(&conflict.reason)
            ));
            out.push_str("    }");
        }
        out.push('\n');
    }
    out.push_str("  ]\n}\n");
    out
}

pub fn write_output(path: &str, data: &str) -> Result<(), String> {
    let path = Path::new(path);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    fs::write(path, data).map_err(|e| e.to_string())
}
