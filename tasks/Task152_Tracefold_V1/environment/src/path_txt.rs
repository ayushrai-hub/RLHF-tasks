use serde_json::Value;
use std::fs;
use std::io;

pub type ResultX<T> = Result<T, String>;

pub fn read_seed_path(p: &str) -> io::Result<Value> {
    let t = fs::read_to_string(p)?;
    serde_json::from_str(&t).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
}

