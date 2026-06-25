use crate::cfg;
use crate::pool::Engine;
use crate::scan::ScenarioMeta;

pub fn apply_manifest_lane(engine: &mut Engine, meta: &ScenarioMeta) {
    let _ = meta;
}

pub fn apply_profile_mask(engine: &mut Engine, _profile: &cfg::Profile) {}
