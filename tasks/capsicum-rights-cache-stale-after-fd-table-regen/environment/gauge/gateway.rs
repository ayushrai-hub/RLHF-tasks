pub fn run_mirror(prism_root: &str, scenario_id: u32) {
    let notes = crate::lens_gauge_r::gauge_f(prism_root, scenario_id);
    crate::lens_shadow_gauge::record_notes(prism_root, notes.len() as u32);
}
