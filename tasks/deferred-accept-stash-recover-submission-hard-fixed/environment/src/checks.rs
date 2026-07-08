use crate::errors::GateError;
use crate::model::Root;

pub fn validate_root(root: &Root) -> Result<(), GateError> {
    if !root.base.is_dir() {
        return Err(GateError::new(20, "workroot missing"));
    }
    crate::walk::layout_ok(root)
}

pub fn validate_tag(tag: &str) -> Result<(), GateError> {
    if tag.is_empty() || tag.contains('|') {
        return Err(GateError::new(21, "invalid tag"));
    }
    Ok(())
}
