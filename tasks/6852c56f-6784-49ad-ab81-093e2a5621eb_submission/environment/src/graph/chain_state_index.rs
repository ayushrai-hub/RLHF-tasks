pub const FALLBACK_DEPTH_REVISION: &str = "rev-fallback-d0";
pub const LIVE_REVISION_PREFIX: &str = "rev-";
pub const STALE_SUFFIX: &str = "-stale";

// Example raw seeds the resolver may see in scenario rows: bare labels like
// "beta-depth" or "beta-depth-stale", and seeds that already carry the live
// prefix like "rev-2026-05" or "rev-2026-05-stale".
pub fn resolve_depth_revision(dep: bool, inact: bool, seed: &str, steps: u64) -> String {
    let _ = (dep, inact, steps, FALLBACK_DEPTH_REVISION, LIVE_REVISION_PREFIX, STALE_SUFFIX);
    seed.to_string()
}
