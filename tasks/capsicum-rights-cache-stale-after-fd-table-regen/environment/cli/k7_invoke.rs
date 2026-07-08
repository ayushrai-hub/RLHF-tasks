use k7_replay::engine;
use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    let mut scenario = 0u32;
    let args: Vec<String> = env::args().collect();
    let mut idx = 1;
    while idx < args.len() {
        if args[idx] == "--scenario" && idx + 1 < args.len() {
            scenario = args[idx + 1].parse().unwrap_or(0);
            idx += 2;
        } else {
            idx += 1;
        }
    }
    let state_dir = PathBuf::from("/app/replay-state");
    let _ = fs::create_dir_all(&state_dir);
    let rows = engine::replay_scenario(scenario, &state_dir);
    engine::save_epoch_cache(scenario, &rows, &state_dir);
}
