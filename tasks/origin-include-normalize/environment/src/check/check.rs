use std::path::Path;

use crate::errors::Err;
use crate::model::Root;

pub fn layout_ok(base: &Path) -> Result<(), Err> {
    let src = base.join("masters");
    if !src.is_dir() {
        return Err(Err::new(50, "masters dir missing"));
    }
    let root_file = src.join("root.master");
    if !root_file.is_file() {
        return Err(Err::new(51, "root.master missing"));
    }
    let _ = Root::new(base.to_path_buf());
    Ok(())
}
