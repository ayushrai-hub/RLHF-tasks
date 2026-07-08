use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use crate::model::Requirement;

pub fn parse_workspace(path: &Path) -> Result<Vec<Requirement>, String> {
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let mut roots = Vec::new();
    for (line_no, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<_> = line.split_whitespace().collect();
        if parts.len() < 4 || parts[0] != "root" {
            return Err(format!("bad workspace line {}", line_no + 1));
        }
        let mut features = BTreeSet::new();
        for token in &parts[4..] {
            if let Some(rest) = token.strip_prefix("features=") {
                features.extend(parse_features(rest)?);
            } else {
                return Err(format!("bad workspace option {token}"));
            }
        }
        roots.push(Requirement {
            package: parts[2].to_string(),
            constraint: parts[3].to_string(),
            features,
        });
    }
    Ok(roots)
}

pub fn parse_features(s: &str) -> Result<BTreeSet<String>, String> {
    let mut out = BTreeSet::new();
    if s.is_empty() {
        return Ok(out);
    }
    for feature in s.split(',') {
        if feature.is_empty() {
            return Err("empty feature".to_string());
        }
        out.insert(feature.to_string());
    }
    Ok(out)
}
