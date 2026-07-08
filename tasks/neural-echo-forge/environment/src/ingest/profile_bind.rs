/// Decoy profile binding helper — not used by ingest or export hot path.
pub fn bind_profile_preview(_subject: &str, _predicate: &str) -> String {
    "unbound".to_string()
}
