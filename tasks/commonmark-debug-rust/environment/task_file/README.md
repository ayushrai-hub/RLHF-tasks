# commonmark

A standard-library-only Rust renderer for the **inline** content of a CommonMark
paragraph: given inline markdown, it produces the HTML that appears between
`<p>` and `</p>`.

Supported inline constructs: backslash escapes, character references, code spans,
emphasis and strong emphasis, inline links and images, and hard/soft line breaks
(CommonMark 0.30). Reference links, autolinks, and raw inline HTML are out of scope.

## Build & run

```
cargo build --release
./target/release/commonmark input_data/cases.json
```

## Behaviour

The authoritative specification lives under `docs/` — start at `docs/MODEL.md`,
then `docs/INLINE.md`, `docs/TEXT.md`, `docs/EMPHASIS.md` (the hardest part), and
`docs/LINKS.md`, with `docs/EXAMPLES.md` for worked vectors and `docs/GLOSSARY.md`
for terms.
