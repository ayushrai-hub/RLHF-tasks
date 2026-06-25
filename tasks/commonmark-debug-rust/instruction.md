There's a std-only Rust crate under `/app/task_file` called `commonmark` that renders
the inline content of a CommonMark paragraph to HTML — the markup that would sit
between the `<p>` and `</p>` of the rendered paragraph. It reads
`input_data/cases.json` and prints one JSON result per `render` op. The implementation
is buggy: it agrees with a correct CommonMark renderer on plenty of inputs but
diverges on others, and the divergences are spread across the scanner, the emphasis
pass, and the text utilities rather than sitting in one place. The hardest part is
emphasis — a naive "match the nearest `*` with the next one" approach gets the
flanking, intraword-underscore, and rule-of-3 cases wrong — but there are also bugs in
code-span matching and normalization, backslash escapes, character references, HTML
escaping, line breaks, links and images (which are resolved together with emphasis on the
same delimiter stack), and image alt text. I need `src/` brought fully in line with the spec so every
op is correct in general; grading runs held-out inputs well beyond the sample file, so
fixing only what you can see in `cases.json` won't be enough.

The authoritative behaviour is under `docs/` and follows CommonMark 0.30 for the
constructs in scope: `docs/MODEL.md` has the CLI, the JSON envelope, the error model,
the scope of the inline grammar, and the HTML escaping; `docs/INLINE.md` covers
backslash escapes, code spans, and line breaks; `docs/TEXT.md` covers character
references and escaping; `docs/EMPHASIS.md` defines the emphasis and strong-emphasis
algorithm precisely — the flanking rules, what can open and close, the rule of 3, and
the delimiter-pairing procedure; `docs/LINKS.md` defines inline links and images and how
brackets resolve on the delimiter stack (including the no-links-in-links rule and image
alt text); and `docs/EXAMPLES.md` has worked vectors. Reference links, autolinks, and raw
inline HTML are out of scope and do not appear in the inputs. Treat the docs as the contract and reconcile the code to them.

A few ground rules. Don't touch `input_data/cases.json` — it must stay byte-for-byte as
shipped, and grading checks its hash. Output has to be deterministic, one result object
per op in input order, with each case `id` echoed verbatim, and an unrecognised op
reports `error` true with an empty `output`. Keep it std-only (no crates may be added
to `Cargo.toml`, and no markdown or regex crate — the renderer is hand-written) and make
sure `cargo build --release` finishes with no warnings. Grading builds the crate in
release mode and runs the resulting `target/release/commonmark` binary against held-out
cases, so the fix has to be a real, general implementation rather than anything keyed to
the sample inputs. The CLI invocation, the JSON in/out shape, and the process exit codes
are fixed.
