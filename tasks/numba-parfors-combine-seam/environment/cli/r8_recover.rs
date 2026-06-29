use r8_replay::engine;
use std::path::PathBuf;

fn main() {
    let state_dir = PathBuf::from("/app/replay-state");
    if !engine::recover_from_wal(&state_dir) {
        std::process::exit(1);
    }
}
