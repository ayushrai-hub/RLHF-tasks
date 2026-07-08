/// Decoy memory seal helper — not used by export hot path.
pub fn seal_preview(_digest: &str) -> String {
    "unsealed".to_string()
}
