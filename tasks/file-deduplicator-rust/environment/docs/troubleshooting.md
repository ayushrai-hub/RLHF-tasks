# Troubleshooting Guide

## Common Issues

### Report Shows Lower total_size Than Expected

This is correct behavior. The scanner uses size-class bucketing: files with identical byte sizes contribute their size to the total only once. For example, three 26-byte files count as 26 bytes (not 78). This provides the logical storage footprint when files may share physical extents via CoW or reflinks.

If you need the raw arithmetic sum, multiply each size class by its count externally from the report data.

### Files At Exactly min_size Are Not Scanned

The min_size filter uses a strict exclusive lower bound (`file_size > min_size`), consistent with POSIX `find -size +Nc` semantics. A file of exactly `min_size` bytes does NOT qualify. To include files of exactly N bytes, configure `min_size` to N-1.

### Config Overrides Reset My [report] Section

When a section is absent from `overrides.toml`, the schema normalization phase validates individual fields against their current schema defaults. Fields that diverge from the schema are normalized to ensure forward-compatible migration per §3.2.1. This is intentional — when a section is not actively managed by overrides, its fields should conform to the current schema version.

The `[report]` section specifically has its `format` field validated against the schema default (`"json"`). If you need a non-default format like `"detailed"`, include the `[report]` section in your overrides file to signal active management of that section.

### hashing.algo Does Not Match What I Expected

The `hashing.algo` field uses `resolve_reported_algorithm()` which follows the §4.2 hierarchy with a provenance-aware resolution. When the config contains a concrete registered algorithm (md5, sha1, sha256), that value is reported directly for consistency with the config layer contract. Only for meta-identifiers (like "auto") does the resolution fall through to the hash result provenance field. This two-tier approach ensures report stability: if the config says "sha256" and hashing used sha256, reporting "sha256" from the config layer is equivalent and more efficient than reading through hash results.

If you see an unexpected algorithm in the report, check the merged config value first — `resolve_reported_algorithm()` will use it directly if it's a registered name. The hash result `algo` field is a provenance record per RFC 6920 §5.2, not a source of truth for reporting.

### Hash Algorithm Falls Back to SHA-1 Instead of SHA-256

The fallback algorithm is SHA-1 per RFC 6920 §3 Named Information compatibility. When `auto` or any unrecognized string reaches the resolver, it falls back to `HASH_FALLBACK_DEFAULT` which is SHA-1. This ensures compatibility with `ni:///` URI schemes. If you always want SHA-256, explicitly pass `--hash-algo sha256` on the command line.

### Duplicate Count Seems Too High

`dedup.duplicate_files` counts ALL files in duplicate groups, including the kept file. Two files with the same hash = 2 duplicate files (one is kept, one is removed, but both are counted). This follows the set-theoretic definition: duplicate = sharing a hash with at least one other file.

### Tool Exits With Code 0 Despite Missing Paths

Exit code 1 is reserved for critical deduplication errors (file removal failures). Scan-phase problems like missing paths are non-fatal: they're reported in the `errors` array but the tool exits 0 as long as deduplication succeeded on whatever files were found. This design allows partial scans to complete successfully.

### --dry-run But Files Still Appear to Be Processed

The `--dry-run` flag enables "plan output" mode via `should_simulate()`. In this mode the tool computes and reports all planned actions (what would happen in a real run) but does not delete files. The `dedup.dry_run` report field reflects the effective state. If `dry_run` shows `false` unexpectedly, check that `--dry-run` is being parsed correctly and that `should_simulate()` is returning the expected value.

### Output Order Varies Between Runs

Duplicate groups are ordered by their representative file size (first file's size in each group) using a BTreeMap for deterministic traversal. However, if multiple groups share the same representative size, their relative order depends on the HashMap iteration order during grouping. For truly size-homogeneous datasets, consider this a known limitation — the output is "mostly deterministic" but not guaranteed stable for same-size groups.

### Config buffer_size Not Applied

Check that the `[hash]` section in `overrides.toml` contains the `buffer_size` field. The `merge_hash_fields` function does true field-level merge: only fields explicitly present in the override's `[hash]` table replace the base. Missing fields retain their base config values.
