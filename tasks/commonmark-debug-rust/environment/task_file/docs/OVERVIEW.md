# Overview

This crate renders the inline content of a CommonMark paragraph to HTML — the
markup that appears between `<p>` and `</p>`. It is standard-library only and
hand-written (no markdown or regex crates).

The supported inline constructs, and where each is specified:

- `MODEL.md` — the CLI, the JSON input/output envelope, the error model, the
  scope of the inline grammar, and HTML escaping.
- `INLINE.md` — backslash escapes, code spans, and line breaks (the left-to-right
  scan).
- `TEXT.md` — character references and HTML escaping.
- `EMPHASIS.md` — emphasis and strong emphasis (the delimiter-run pairing
  algorithm). This is the hardest part; read it carefully.
- `LINKS.md` — inline links and images, resolved together with emphasis on the
  same delimiter stack.
- `EXAMPLES.md` — additional worked vectors.
- `GLOSSARY.md` — shared terms.

These documents follow CommonMark 0.30 for the constructs in scope. Links,
images, autolinks, and raw inline HTML are out of scope.

## Source layout

- `src/parse.rs` — the single-pass inline parser (escapes, code spans,
  references, breaks, brackets/links, and the emphasis delimiter-pairing pass).
- `src/text.rs` — character classification, reference decoding, HTML escaping.
- `src/node.rs` — the inline node arena.
- `src/render.rs` — rendering the node list to HTML.
- `src/json.rs`, `src/main.rs` — JSON and the CLI.
