use std::fs;
use std::path::Path;

use crate::errors::GateError;
use crate::model::Root;

pub fn copy_sample(sample: &str, root: &Root) -> Result<(), GateError> {
    let src = Path::new("/app/environment/samples").join(sample);
    if !src.is_dir() {
        return Err(GateError::new(10, format!("missing sample {sample}")));
    }
    if root.base.exists() {
        fs::remove_dir_all(&root.base).map_err(|e| GateError::new(11, e.to_string()))?;
    }
    fs::create_dir_all(&root.base).map_err(|e| GateError::new(12, e.to_string()))?;
    for entry in fs::read_dir(&src).map_err(|e| GateError::new(13, e.to_string()))? {
        let entry = entry.map_err(|e| GateError::new(14, e.to_string()))?;
        let name = entry.file_name();
        let dst = root.base.join(name);
        fs::copy(entry.path(), dst).map_err(|e| GateError::new(15, e.to_string()))?;
    }
    Ok(())
}

pub fn layout_ok(root: &Root) -> Result<(), GateError> {
    if !root.seed_file().exists() {
        return Err(GateError::new(16, "seed.txt missing"));
    }
    Ok(())
}
