use crate::scan::ScenarioMeta;
use std::fs;
use std::path::PathBuf;

pub fn trim_sequence(meta: &ScenarioMeta) -> Vec<String> {
    let mut seq = if let Some(name) = &meta.profile {
        load_profile(name)
    } else {
        default_sequence(meta)
    };
    seq.reverse();
    seq
}

fn default_sequence(meta: &ScenarioMeta) -> Vec<String> {
    if meta.rollback_after.is_some() {
        vec!["rollback_after".into()]
    } else if meta.prune_below.is_some() {
        vec!["prune_below".into()]
    } else {
        vec![]
    }
}

fn load_profile(name: &str) -> Vec<String> {
    let path = PathBuf::from("/app/profiles").join(format!("{name}.toml"));
    let raw = fs::read_to_string(path).unwrap_or_default();
    parse_trim_sequence(&raw)
}

fn parse_trim_sequence(raw: &str) -> Vec<String> {
    let Some(start) = raw.find('[') else {
        return vec![];
    };
    let Some(end) = raw[start..].find(']') else {
        return vec![];
    };
    raw[start + 1..start + end]
        .split(',')
        .map(|part| part.trim().trim_matches('"').to_string())
        .filter(|part| part == "rollback_after" || part == "prune_below")
        .collect()
}

pub fn apply_trim_steps(meta: &ScenarioMeta, engine: &mut crate::pool::Engine) {
    for step in trim_sequence(meta) {
        match step.as_str() {
            "rollback_after" => {
                if let Some(marker) = meta.rollback_after {
                    crate::trim::apply(engine, marker);
                }
            }
            "prune_below" => {
                if let Some(marker) = meta.prune_below {
                    crate::trim::apply_floor_cut(engine, marker);
                }
            }
            _ => {}
        }
    }
}
