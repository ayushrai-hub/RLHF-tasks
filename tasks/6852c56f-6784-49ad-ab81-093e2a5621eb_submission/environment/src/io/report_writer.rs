use crate::model::Report;
use std::fs;
use std::path::Path;

pub fn write_report(path: &str, report: &Report) {
    if let Some(p) = Path::new(path).parent() {
        fs::create_dir_all(p).expect("mkdir");
    }
    fs::write(path, serde_json::to_string_pretty(report).unwrap()).expect("write");
}
