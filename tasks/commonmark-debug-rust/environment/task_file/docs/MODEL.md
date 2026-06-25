# Model: CLI, I/O envelope, and the render operation

This crate renders the **inline** content of a CommonMark paragraph to HTML — the
HTML that would appear between the `<p>` and `</p>` of the rendered paragraph.
It reads a JSON file of cases and prints a JSON document of results.

## CLI

```
commonmark <cases.json>
```

The single argument is the path to the input file. With the wrong number of
arguments, an unreadable file, or input that is not a JSON array, the program
prints a diagnostic to stderr and exits with code 2. On success it prints the
result document to stdout and exits 0. Output must be deterministic.

## Input

A JSON array of cases. Each case is an object:

```json
{ "id": "<string>", "ops": [ <op>, <op>, ... ] }
```

Each `<op>` is an object whose `op` field names the operation. The only
operation is `"render"`, whose operand is `text` (the inline content to render):

```json
{ "op": "render", "text": "<inline CommonMark>" }
```

A missing `text` is treated as the empty string.

## Output

A JSON array with one object per input case, in input order, each echoing the
case `id`:

```json
{ "id": "<string>", "results": [ { "op": "<string>", "output": "<string>", "error": <bool> }, ... ] }
```

`results` has one entry per op, in order. On success `error` is `false` and
`output` is the rendered inline HTML. A request whose `op` is not `"render"` is
an error: `error` is `true` and `output` is the empty string. Object keys are
emitted in the order shown.

## Scope of the inline grammar

The grading inputs are the inline content of a single paragraph, in ASCII, and
exercise exactly these inline constructs:

- backslash escapes (`docs/INLINE.md`),
- character references — numeric and a fixed named set (`docs/TEXT.md`),
- code spans (`docs/INLINE.md`),
- emphasis and strong emphasis (`docs/EMPHASIS.md`),
- inline links and images (`docs/LINKS.md`),
- hard and soft line breaks (`docs/INLINE.md`).

Reference links, autolinks, and raw inline HTML are **out of scope** and do not
appear in the grading inputs. The behaviour follows CommonMark 0.30 for the
constructs above.

## HTML escaping

When literal text is written to the output, `&`, `<`, `>` and `"` are escaped as
`&amp;`, `&lt;`, `&gt;` and `&quot;` respectively; all other characters are
written as-is. This applies to ordinary text and to the contents of a code span.
