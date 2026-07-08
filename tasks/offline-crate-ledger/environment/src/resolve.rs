use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use crate::lock::lock_json;
use crate::model::{Conflict, Requirement, VersionRecord};
use crate::options::Options;
use crate::registry::parse_registry;
use crate::version::satisfies_all;

pub fn resolve(opts: &Options, roots: Vec<Requirement>) -> Result<String, Vec<Conflict>> {
    let registry = Path::new(&opts.registry);
    let mut selected: BTreeMap<String, VersionRecord> = BTreeMap::new();
    let mut features: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut constraints: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut cache: BTreeMap<String, Vec<VersionRecord>> = BTreeMap::new();
    let mut conflicts = Vec::new();

    let mut worklist: Vec<Requirement> = roots.clone();
    for root in &roots {
        features
            .entry(root.package.clone())
            .or_default()
            .extend(root.features.clone());
    }

    let mut pos = 0;
    while pos < worklist.len() {
        let req = worklist[pos].clone();
        pos += 1;

        constraints
            .entry(req.package.clone())
            .or_default()
            .insert(req.constraint.clone());
        features
            .entry(req.package.clone())
            .or_default()
            .extend(req.features.clone());

        if selected.contains_key(&req.package) {
            continue;
        }

        let records = match cache.get(&req.package) {
            Some(r) => r.clone(),
            None => match parse_registry(registry, &req.package) {
                Ok(parsed) => {
                    cache.insert(req.package.clone(), parsed.clone());
                    parsed
                }
                Err(e) => {
                    conflicts.push(Conflict {
                        package: req.package.clone(),
                        constraints: constraints
                            .get(&req.package)
                            .cloned()
                            .unwrap_or_default()
                            .into_iter()
                            .collect(),
                        reason: e,
                    });
                    continue;
                }
            },
        };

        match choose_version(&req.package, &records, &constraints) {
            Ok(chosen) => {
                let pkg_features = features.get(&req.package).cloned().unwrap_or_default();
                let mut active = chosen.deps.clone();
                for feature in &pkg_features {
                    if let Some(reqs) = chosen.feature_deps.get(feature) {
                        active.extend(reqs.clone());
                    }
                }
                for dep in active {
                    worklist.push(dep);
                }
                selected.insert(req.package.clone(), chosen);
            }
            Err(conflict) => {
                conflicts.push(conflict);
            }
        }
    }

    if !conflicts.is_empty() {
        conflicts.sort_by(|a, b| a.package.cmp(&b.package));
        return Err(conflicts);
    }

    Ok(lock_json(&selected, &features))
}

fn choose_version(
    package: &str,
    records: &[VersionRecord],
    constraints: &BTreeMap<String, BTreeSet<String>>,
) -> Result<VersionRecord, Conflict> {
    for record in records.iter().rev() {
        if constraints
            .get(package)
            .unwrap()
            .iter()
            .all(|c| satisfies_all(&record.version, c))
        {
            return Ok(record.clone());
        }
    }
    Err(Conflict {
        package: package.to_string(),
        constraints: constraints
            .get(package)
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .collect(),
        reason: "no matching version".to_string(),
    })
}
