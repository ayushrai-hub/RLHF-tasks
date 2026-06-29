pub fn gateway_epoch(case_root: &str) -> u32 {
    let path = std::path::Path::new(case_root).join("i0.tab");
    crate::d3_d3_b::read_crl_epoch(&path).0
}
