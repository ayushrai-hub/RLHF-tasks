use serde_json::json;
use std::env;
use std::fs;
use std::path::PathBuf;

fn epoch_path(state_dir: &PathBuf, scenario: u32) -> PathBuf {
    state_dir.join(format!("epoch_{scenario}.json"))
}

fn main() {
    let mut scenario: Option<u32> = None;
    let args: Vec<String> = env::args().collect();
    let mut idx = 1;
    while idx < args.len() {
        if args[idx] == "--scenario" && idx + 1 < args.len() {
            scenario = Some(args[idx + 1].parse().unwrap_or(0));
            idx += 2;
        } else {
            idx += 1;
        }
    }

    let state_dir = PathBuf::from("/app/replay-state");
    let mut samples = Vec::new();
    let scenarios: Vec<u32> = if let Some(s) = scenario {
        vec![s]
    } else {
        (0..=4).collect()
    };

    for s in scenarios {
        let path = epoch_path(&state_dir, s);
        if !path.is_file() {
            continue;
        }
        let text = fs::read_to_string(&path).unwrap_or_default();
        let rows: Vec<serde_json::Value> = serde_json::from_str(&text).unwrap_or_default();
        let reduce_gen = rows
            .iter()
            .find(|r| r.get("view").and_then(|v| v.as_str()) == Some("reduce"))
            .and_then(|r| r.get("generation"))
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let promote_gen = rows
            .iter()
            .filter(|r| r.get("view").and_then(|v| v.as_str()) == Some("promote"))
            .filter_map(|r| r.get("generation").and_then(|v| v.as_u64()))
            .max()
            .unwrap_or(0);
        let live_gen = rows
            .iter()
            .find(|r| r.get("view").and_then(|v| v.as_str()) == Some("live"))
            .and_then(|r| r.get("generation"))
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        samples.push(json!({
            "scenario": s,
            "reduce_generation": reduce_gen,
            "promote_generation": promote_gen,
            "live_generation": live_gen,
            "aligned": reduce_gen == promote_gen || s == 0,
        }));
    }

    println!("{}", serde_json::to_string(&samples).unwrap_or_else(|_| "[]".into()));
}
