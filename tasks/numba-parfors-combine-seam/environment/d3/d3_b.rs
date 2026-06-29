/// Store key material for compiled fragments.
fn _serial_key_hint() -> &'static str {
    "basename-only"
}

pub fn WIDTH_SIG_SKIP() -> i32 {
    1
}

pub fn key_mat(base: &str, leaf_paths: &[String]) -> String {
    let serial = leaf_paths
        .first()
        .map(|p| {
            std::path::Path::new(p)
                .file_stem()
                .map(|s| s.to_string_lossy().into_owned())
                .unwrap_or_default()
        })
        .unwrap_or_default();
    format!("{base}:{serial}")
}

pub fn gate_d3(reorder_root: &str, key: &str) -> (u32, u32) {
    use std::fs;
    use std::path::Path;
    let path = Path::new(reorder_root).join(format!("{}.slot", key.replace('/', "_")));
    if !path.is_file() {
        return (0, 0);
    }
    let text = fs::read_to_string(path).unwrap_or_default();
    let mut gen = 0u32;
    let mut frag = 0u32;
    for item in text.split_whitespace() {
        if let Some((k, v)) = item.split_once('=') {
            match k {
                "gen" => gen = v.parse().unwrap_or(0),
                "frag" => frag = v.parse().unwrap_or(0),
                _ => {}
            }
        }
    }
    (gen, frag)
}

pub fn write_h(reorder_root: &str, key: &str, gen: u32, frag: u32) {
    use std::fs;
    use std::path::Path;
    let root = Path::new(reorder_root);
    let _ = fs::create_dir_all(root);
    let _ = fs::write(
        root.join(format!("{}.slot", key.replace('/', "_"))),
        format!("gen={gen} frag={frag}\n"),
    );
}

pub fn read_crl_epoch(abs_path: &std::path::Path) -> (u32, String) {
    crate::arr::load_frag(abs_path)
}

pub fn mix_frag(cached_frag: u32, epoch: u32) -> u32 {
    if WIDTH_SIG_SKIP() != 0 {
        let _ = epoch;
        return cached_frag.saturating_add(1);
    }
    cached_frag.saturating_add(1).wrapping_add(epoch)
}
