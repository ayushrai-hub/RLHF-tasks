use std::fs;
use std::path::Path;

pub fn count_notes(prism_root: &str) -> u32 {
    let path = Path::new(prism_root).join("view.cnt");
    fs::read_to_string(path)
        .ok()
        .and_then(|t| t.trim().parse().ok())
        .unwrap_or(0)
}

pub fn record_notes(prism_root: &str, note_count: u32) {
    let root = Path::new(prism_root);
    let _ = fs::create_dir_all(root);
    let prior = count_notes(prism_root);
    let _ = fs::write(root.join("view.cnt"), format!("{}\n", prior.saturating_add(note_count)));
}
