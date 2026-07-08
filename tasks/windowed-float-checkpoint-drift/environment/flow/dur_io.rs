use std::path::Path;

use crate::agg::{AggErr, PartialFrame};
use crate::ckpt::frame_c4::{read_frame_c4, write_frame_c4};

pub fn persist_frame(path: &Path, frame: &PartialFrame) -> Result<(), AggErr> {
    write_frame_c4(path, frame)
}

pub fn hydrate_frame(path: &Path) -> Result<PartialFrame, AggErr> {
    read_frame_c4(path)
}
