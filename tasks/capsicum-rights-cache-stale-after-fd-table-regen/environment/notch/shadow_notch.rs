use std::fs;
use std::path::Path;

pub fn log_hit(meta_root: &str, key: &str) {
    let root = Path::new(meta_root);
    let _ = fs::create_dir_all(root.join("stats"));
    let _ = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(root.join("stats/hits.log"));
    let _ = fs::write(root.join("stats/last_key.txt"), key);
}
