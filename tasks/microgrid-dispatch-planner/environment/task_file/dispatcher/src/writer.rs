use std::fs;
use std::path::Path;

use crate::types::Dispatch;

pub fn write_dispatch(path: &Path, dispatch: &Dispatch) {
    let json = serde_json::to_string_pretty(dispatch).expect("serialize dispatch");
    fs::write(path, json).expect("write dispatch.json");
}
