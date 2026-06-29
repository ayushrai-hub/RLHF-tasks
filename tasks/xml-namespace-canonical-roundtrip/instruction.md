This is a source-fix task: repair the Go source under `/app/environment` so the `nsx` XML namespace canonicalizer works end to end. A fresh `make install` must produce a working binary; patching generated artifacts or task-checker files is not acceptable.

Downstream import jobs compare documents by expanded names, replay prior runs, reuse output directories across batches, and rebuild member directories from list files. From `/app/environment`:

```bash
make install
nsx build --input /path/to/input.xml --out /path/to/out-dir
nsx validate --input /path/to/input.xml --artifact /path/to/out-dir
nsx replay --input /path/to/input.xml --artifact /path/to/out-dir
nsx batch --list /path/to/list.txt --out /path/to/batch-out
```

Single-input builds write `/app/output/nsx-run/canonical.xml`, `/app/output/nsx-run/scope.json`, `/app/output/nsx-run/audit.jsonl`, and `/app/output/nsx-run/.nsx-input`. Batch builds create one member directory per list entry under the batch output root (named from each input basename) and write `/path/to/batch-out/batch.jsonl` (example batch ledger path: `/app/output/nsx-run/batch.jsonl`) with rows sorted by input path. Each batch row records `input`, `artifact_dir`, and `canonical_sha256` for the member canonical XML bytes. Re-running batch on the same output root must replace the ledger and rebuild only the listed members, removing member directories that are no longer listed.

`/app/environment/docs/contract.md` is normative for artifact schemas and command behavior. Canonical XML uses generated root prefixes in lexicographic URI order (`namespace_prefix_order`), attributes sorted by namespace URI then local name then value (`attribute_sort`), collapsed non-empty text (`whitespace_normalization`), and correct default-namespace reset handling (`default_namespace_reset`). Scope JSON uses version `nsx-scope-v1`, lists only used namespace URIs in `namespace_uris`, records expanded node and attribute names (`node_expanded_names`, `attributes`), and stores element-local namespace declarations in each node's `declared` array without inherited parent bindings. Audit JSONL records the `phase_sequence` `parse`, `normalize`, `serialize`, `validate` with `status`, `input_output_paths`, and timestamps on each row.

The canonicalizer must implement Namespaces-in-XML semantics across parse, normalization, emission, scope reporting, validation, replay, and batch rebuild. Namespace declarations establish in-scope bindings for an element and its descendants; nearer declarations take precedence and bindings restored after an inner scope ends must not leak to later siblings. Default namespaces apply to unprefixed elements but not to unprefixed attributes. An empty default declaration (`xmlns=""`) clears the current default element namespace for that subtree. Prefixed elements and attributes resolve through the nearest binding. Two regular attributes sharing the same expanded `(namespace URI, local name)` must be rejected even when their values differ.

Equivalent inputs that differ only by prefix spelling, declaration order, redundant unused declarations, insignificant whitespace, or default-versus-prefixed spelling must converge to the same canonical XML, matching scope metadata for actually used namespace URIs, and identical `canonical_sha256` values in batch mode. Validation and replay must confirm stored `scope.json` and `canonical.xml` still match a fresh parse and normalization of the same input, including expanded node names, attributes, and element-local `declared` entries.
