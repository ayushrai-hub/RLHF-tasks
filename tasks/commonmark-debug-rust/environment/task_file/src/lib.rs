//! A standard-library-only Rust implementation of CommonMark inline rendering:
//! given the inline content of a paragraph, produce the inline HTML. The
//! supported inline constructs are backslash escapes, character references,
//! code spans, emphasis and strong emphasis, links and images, and hard/soft
//! line breaks. The `docs/` directory is the authoritative specification — start
//! at `docs/MODEL.md`.

pub mod error;
pub mod json;
pub mod node;
pub mod parse;
pub mod render;
pub mod text;

pub use error::{Error, Result};

/// Render the inline CommonMark content `input` to inline HTML.
pub fn render_inline(input: &str) -> String {
    let nodes = parse::parse(input);
    render::render(&nodes)
}
