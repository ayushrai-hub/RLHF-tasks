use std::collections::{BTreeMap, BTreeSet};

use crate::model::VersionRecord;

pub fn lock_json(
    selected: &BTreeMap<String, VersionRecord>,
    features: &BTreeMap<String, BTreeSet<String>>,
) -> String {
    let mut out = String::from("{\n  \"packages\": [\n");
    for (idx, (name, record)) in selected.iter().enumerate() {
        if idx > 0 {
            out.push_str(",\n");
        }
        let empty = BTreeSet::new();
        let feats = features.get(name).unwrap_or(&empty);
        let mut dep_names = BTreeSet::new();
        for dep in &record.deps {
            dep_names.insert(dep.package.clone());
        }
        for feature in feats {
            if let Some(reqs) = record.feature_deps.get(feature) {
                for dep in reqs {
                    dep_names.insert(dep.package.clone());
                }
            }
        }
        let deps: Vec<(String, String)> = dep_names
            .into_iter()
            .filter_map(|name| selected.get(&name).map(|r| (name, r.version.raw.clone())))
            .collect();
        out.push_str("    {\n");
        out.push_str(&format!("      \"name\": \"{}\",\n", esc(name)));
        out.push_str(&format!(
            "      \"version\": \"{}\",\n",
            esc(&record.version.raw)
        ));
        out.push_str("      \"features\": [");
        for (fidx, feature) in feats.iter().enumerate() {
            if fidx > 0 {
                out.push_str(", ");
            }
            out.push_str(&format!("\"{}\"", esc(feature)));
        }
        out.push_str("],\n");
        out.push_str("      \"dependencies\": [");
        if !deps.is_empty() {
            out.push('\n');
            for (didx, (dep, version)) in deps.iter().enumerate() {
                if didx > 0 {
                    out.push_str(",\n");
                }
                out.push_str(&format!(
                    "        {{\"name\": \"{}\", \"version\": \"{}\"}}",
                    esc(dep),
                    esc(version)
                ));
            }
            out.push_str("\n      ");
        }
        out.push_str("]\n");
        out.push_str("    }");
    }
    out.push_str("\n  ]\n}\n");
    out
}

pub fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}
