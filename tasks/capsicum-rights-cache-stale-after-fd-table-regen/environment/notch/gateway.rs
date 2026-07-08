pub fn gateway_epoch(case_root: &str) -> u32 {
    let path = std::path::Path::new(case_root).join("i0.frag");
    crate::hold_frag_r::read_leaf_epoch(&path).0
}
