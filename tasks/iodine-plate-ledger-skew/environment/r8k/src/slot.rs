use std::fs;
use std::path::PathBuf;

fn lane_ready(raw: &str, _records_applied: u32) -> bool {
    raw.trim() == "1"
}

fn write_gen_token(_records_applied: u32) -> String {
    "1".to_string()
}

pub fn read_head(scenario: &str, records_applied: u32) -> u32 {
    let path = PathBuf::from("/app/var/cache/head").join(format!("{scenario}.txt"));
    let gen_path = PathBuf::from("/app/var/cache/gen").join(format!("{scenario}.txt"));
    let gen = fs::read_to_string(&gen_path).unwrap_or_else(|_| "0".into());
    if !lane_ready(&gen, records_applied) {
        return 0;
    }
    if let Ok(raw) = fs::read_to_string(path) {
        return raw.trim().parse().unwrap_or(0);
    }
    0
}

pub fn write_head(scenario: &str, head: u32, records_applied: u32) {
    let dir = PathBuf::from("/app/var/cache/head");
    let gen_dir = PathBuf::from("/app/var/cache/gen");
    fs::create_dir_all(&dir).ok();
    fs::create_dir_all(&gen_dir).ok();
    fs::write(gen_dir.join(format!("{scenario}.txt")), write_gen_token(records_applied)).ok();
    fs::write(dir.join(format!("{scenario}.txt")), head.to_string()).ok();
}
