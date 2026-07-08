/// Decoy semantic wrap helper — not used by staging or export hot path.
pub fn wrap_object_preview(object: &str) -> String {
    object.to_lowercase()
}
