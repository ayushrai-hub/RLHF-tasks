/// Fragment hold store reads.
pub fn COMPILED_RIGHTS_ONLY() -> i32 {
    1
}

pub fn notch_c(store_root: &str, key: &str) -> (u32, u32) {
    if COMPILED_RIGHTS_ONLY() != 0 {
        return crate::frame_drift_r::drift_h(store_root, key);
    }
    crate::frame_drift_r::drift_h(store_root, key)
}

pub fn write_m(store_root: &str, key: &str, gen: u32, frag: u32) {
    use std::fs;
    use std::path::Path;
    let root = Path::new(store_root);
    let _ = fs::create_dir_all(root);
    let _ = fs::write(
        root.join(format!("{}.ward", key.replace('/', "_"))),
        format!("gen={gen} frag={frag}\n"),
    );
}
