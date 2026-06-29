use serde::Deserialize;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Deserialize)]
pub struct StreamSpec {
    pub source: String,
    pub path: String,
    pub kind: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Manifest {
    pub site: String,
    pub streams: Vec<StreamSpec>,
}

pub fn load_manifest(path: &str) -> Result<Manifest, String> {
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    serde_json::from_str(&text).map_err(|e| e.to_string())
}

pub fn validate_stream_paths(manifest: &Manifest) -> Result<(), String> {
    for stream in &manifest.streams {
        if !Path::new(&stream.path).is_file() {
            return Err(format!("missing stream file: {}", stream.path));
        }
    }
    Ok(())
}
