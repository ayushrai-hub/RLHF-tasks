# nsx artifact and command contract

`nsx` canonicalizes XML by expanded namespace names. The command-line surface is `build`, `validate`, `replay`, and `batch`.

## Commands

- `nsx build --input PATH --out DIR` parses and normalizes the input, writes artifacts under `DIR`, and records audit rows.
- `nsx validate --input PATH --artifact DIR` re-parses the input, re-normalizes it, confirms duplicate-attribute rules, verifies `canonical.xml` matches a fresh render, verifies full `scope.json` content against the parsed document, and checks audit hygiene.
- `nsx replay --input PATH --artifact DIR` performs the same cross-artifact consistency checks as `validate` and additionally requires the stored input marker to match the supplied `--input` path.
- `nsx batch --list PATH --out DIR` reads one input XML path per line from `PATH`, builds each input into `DIR/<basename>/`, writes `DIR/batch.jsonl`, and replaces any prior batch ledger. Member directories whose basenames are absent from the new list must be removed before rebuilding.

## Batch ledger

`batch.jsonl` contains one JSON object per list entry, sorted by `input` path. Each row contains:

- `input`: absolute or relative input path from the list file
- `artifact_dir`: member directory holding that input's artifacts
- `canonical_sha256`: lowercase hex SHA-256 of the member `canonical.xml` bytes

Equivalent inputs must produce identical `canonical_sha256` values.

## Output directory lifecycle

Each build replaces prior `canonical.xml`, `scope.json`, `audit.jsonl`, and `.nsx-input` contents for the output directory. Temporary files ending in `.tmp` and stale marker files from earlier runs must not remain after a successful build.

The `.nsx-input` marker stores the absolute input path used for the artifact set currently present in the directory.

## canonical.xml

UTF-8 XML ending with one trailing newline. Namespace URIs that appear on emitted element or attribute names are declared once at the document root using generated prefixes `n0`, `n1`, … assigned in lexicographic URI order. Unprefixed elements and attributes remain unprefixed. Attributes on each element are sorted by namespace URI, then local name, then value. Insignificant whitespace-only text nodes are omitted; other character content collapses internal runs of whitespace to a single ASCII space.

## scope.json

Version string `nsx-scope-v1`. Top-level fields: `version`, `input`, `namespace_uris`, `nodes`.

- `namespace_uris` lists each namespace URI that appears on any emitted element or attribute name in the document, sorted lexicographically. URIs that are declared but never used on an element or attribute name must not appear.
- Each node entry contains `path`, `name`, `declared`, and `attributes`.
- `declared` lists only namespace declarations present on that element's start tag, not bindings inherited from ancestors.
- Each attribute entry contains `uri`, `local`, and `value`.

## audit.jsonl

One JSON object per line, in this order: `parse`, `normalize`, `serialize`, `validate`. Each row contains `phase`, `status`, `input`, `output`, and `unix_ms`. Successful builds use `status=ok` for all four phases.
