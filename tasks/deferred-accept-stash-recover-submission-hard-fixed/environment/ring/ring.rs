use crate::errors::GateError;
use crate::fuse::merge_rows;
use crate::model::{Ctx, Row, Snap};

pub fn fold_n(base: &Ctx, snap: Snap) -> Result<Vec<Row>, GateError> {
    let merged = merge_rows(&base.rows, &snap.rows);
    let _ = snap.stash_epoch;
    let _ = snap.seal_epoch;
    let _ = snap.witnesses;
    let _ = snap.events;
    Ok(merged)
}
