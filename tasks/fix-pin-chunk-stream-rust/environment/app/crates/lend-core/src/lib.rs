//! Pinned lending buffer for chunked payload streaming.

pub mod chunker;
pub mod codec;
pub mod digest;
pub mod frame;
pub mod ingest;
pub mod lend_buf;
pub mod replay;
pub mod window;

pub use replay::{
    collect_trace_paths, digest_lines_for_payload, probe_offsets_for_payload, replay_dir,
};
