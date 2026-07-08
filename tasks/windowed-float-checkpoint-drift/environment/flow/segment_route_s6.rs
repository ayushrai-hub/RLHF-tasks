use std::path::Path;

use crate::agg::{AggErr, EventRow};
use crate::flow::wal_j3::replay_wal_j3;

pub fn split_wal_tail(
    wal_rows: &[EventRow],
    tail_fixture: &[EventRow],
    frame_wm: u64,
    frame_processed: u64,
) -> (Vec<EventRow>, Vec<EventRow>) {
    let _ = frame_wm;
    let late: Vec<EventRow> = wal_rows
        .iter()
        .filter(|ev| ev.seq <= frame_processed)
        .cloned()
        .collect();
    let live: Vec<EventRow> = tail_fixture
        .iter()
        .filter(|ev| ev.seq > frame_processed)
        .cloned()
        .collect();
    (late, live)
}

pub fn routed_tail_rows(
    wal_path: &Path,
    tail_fixture: &[EventRow],
    frame_wm: u64,
    frame_processed: u64,
    frame_gen: u64,
) -> Result<(Vec<EventRow>, Vec<EventRow>, Vec<EventRow>), AggErr> {
    let wal_rows = replay_wal_j3(wal_path, frame_gen)?;
    let (late, live) = split_wal_tail(&wal_rows, tail_fixture, frame_wm, frame_processed);
    Ok((wal_rows, late, live))
}

pub fn route_preview_count(wal_rows: &[EventRow], frame_processed: u64) -> usize {
    wal_rows
        .iter()
        .filter(|ev| ev.seq <= frame_processed)
        .count()
}
