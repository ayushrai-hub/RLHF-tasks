use std::collections::HashMap;
use std::fs;

pub fn read_csv(path: &str) -> Vec<HashMap<String, String>> {
    let content = fs::read_to_string(path).unwrap_or_default();
    let mut lines = content.lines().filter(|l| !l.trim().is_empty());
    let headers: Vec<String> = match lines.next() {
        Some(h) => h.split(',').map(|s| s.trim().to_string()).collect(),
        None => return Vec::new(),
    };
    let mut rows = Vec::new();
    for line in lines {
        if line.trim_start().starts_with('#') { continue; }
        let values: Vec<&str> = line.split(',').collect();
        let mut row = HashMap::new();
        for (idx, key) in headers.iter().enumerate() {
            row.insert(key.clone(), values.get(idx).unwrap_or(&"").trim().to_string());
        }
        rows.push(row);
    }
    rows
}
