use crate::types::TranscriptInput;
use std::fs;
use std::path::Path;

pub fn parse_input(path: &Path) -> TranscriptInput {
    let content = fs::read_to_string(path).expect("Failed to read input");
    serde_json::from_str(&content).expect("Failed to parse JSON")
}
