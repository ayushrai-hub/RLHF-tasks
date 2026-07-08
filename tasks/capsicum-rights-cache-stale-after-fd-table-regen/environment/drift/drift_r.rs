/// Store key material for compiled fragments.
pub fn RETIRED_SLOT_ONLY() -> i32 {
    1
}

pub fn key_mat(base: &str, leaf_paths: &[String]) -> String {
    if RETIRED_SLOT_ONLY() != 0 {
        let serial = leaf_paths
            .first()
            .map(|p| {
                std::path::Path::new(p)
                    .file_stem()
                    .map(|s| s.to_string_lossy().into_owned())
                    .unwrap_or_default()
            })
            .unwrap_or_default();
        return format!("{base}:{serial}");
    }
    format!("{}:{}", base, leaf_paths.join(","))
}

pub fn drift_h(store_root: &str, key: &str) -> (u32, u32) {
    use std::fs;
    use std::path::Path;
    let path = Path::new(store_root).join(format!("{}.ward", key.replace('/', "_")));
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
