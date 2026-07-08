use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use crate::model::{Requirement, VersionRecord};
use crate::version::Version;
use crate::workspace::parse_features;

pub fn parse_registry(registry: &Path, package: &str) -> Result<Vec<VersionRecord>, String> {
    let path = registry.join(format!("{package}.pkg"));
    let text = fs::read_to_string(&path).map_err(|_| format!("missing package {package}"))?;
    let mut records: Vec<VersionRecord> = Vec::new();
    for (line_no, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<_> = line.split_whitespace().collect();
        match parts.first().copied() {
            Some("version") => {
                if parts.len() < 2 {
                    return Err(format!("bad version line {} in {package}", line_no + 1));
                }
                let mut yanked = false;
                for token in &parts[2..] {
                    if *token == "yanked=true" {
                        yanked = true;
                    } else {
                        return Err(format!("bad version option {token} in {package}"));
                    }
                }
                records.push(VersionRecord {
                    version: Version::parse(parts[1])?,
                    yanked,
                    deps: Vec::new(),
                    feature_deps: BTreeMap::new(),
                });
            }
            Some("dep") => {
                let dep = parse_dep_line(&parts, package, line_no + 1, 1)?;
                records
                    .last_mut()
                    .ok_or_else(|| format!("dep before version in {package}"))?
                    .deps
                    .push(dep);
            }
            Some("feature") => {
                if parts.len() < 4 {
                    return Err(format!("bad feature line {} in {package}", line_no + 1));
                }
                let feature_name = parts[1].to_string();
                let dep = parse_dep_line(&parts, package, line_no + 1, 2)?;
                records
                    .last_mut()
                    .ok_or_else(|| format!("feature before version in {package}"))?
                    .feature_deps
                    .entry(feature_name)
                    .or_default()
                    .push(dep);
            }
            _ => return Err(format!("bad registry line {} in {package}", line_no + 1)),
        }
    }
    records.sort_by(|a, b| a.version.cmp(&b.version));
    Ok(records)
}

fn parse_dep_line(
    parts: &[&str],
    package: &str,
    line_no: usize,
    start: usize,
) -> Result<Requirement, String> {
    if parts.len() < start + 2 {
        return Err(format!("bad dependency line {line_no} in {package}"));
    }
    let mut features = std::collections::BTreeSet::new();
    for token in &parts[start + 2..] {
        if let Some(rest) = token.strip_prefix("features=") {
            features.extend(parse_features(rest)?);
        } else {
            return Err(format!("bad dependency option {token} in {package}"));
        }
    }
    Ok(Requirement {
        package: parts[start].to_string(),
        constraint: parts[start + 1].to_string(),
        features,
    })
}
