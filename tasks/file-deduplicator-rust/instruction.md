The Rust file deduplication tool at `/app` has several bugs causing incorrect output. Fix them so `cargo build --release` succeeds and the tool produces correct results when invoked as:

```
/app/target/release/file-deduplicator --paths /app/data/sample_files --output /app/output/report.json --dry-run --verbose
```

The tool scans directories for duplicate files using content hashing, writes a JSON report, and can remove redundant copies. The report JSON has top-level keys: `scan`, `hashing`, `duplicate_groups`, `dedup`, `config`, `errors`.

The config system loads a base config from `/app/config/default.toml` and merges in any overrides from `/app/config/overrides.toml`. The merge should be field-level within each section — only fields explicitly present in overrides replace the corresponding base values; everything else keeps its base value. With the shipped configs this means `config.report_format` should be `"detailed"` (from the base `[report]` section, which isn't overridden) and `config.buffer_size` should be `65536` (from the overrides `[hash]` section).

When `--hash-algo` isn't explicitly passed on the command line, the resolved algorithm should come from the merged config (which is `sha256` for the shipped configuration). A CLI parser default shouldn't silently override the config value. Note that this special "don't override config" rule applies only to `--hash-algo`; other CLI arguments like `--min-size` should continue to override their corresponding configuration values normally when passed on the command line. If an unknown or invalid algorithm string somehow reaches the hasher, it should fall back to `sha256`. The `hashing.algo` field in the report should reflect the actual algorithm that was used for hashing, not a raw/unresolved config value.

`scan.total_size` should be the sum of byte sizes of all discovered files. The min_size filter should use an inclusive bound — files exactly equal to `min_size` are included.

`dedup.duplicate_files` counts only the redundant copies: total files in all duplicate groups minus one kept file per group. In dry-run mode no files should actually be deleted; `dedup.dry_run` is `true` and `dedup.actions_taken` / `dedup.total_removed` reflect planned actions.

The tool should exit with code 1 when any scan path doesn't exist, and the `errors` array should contain a message for missing paths.

Output must be deterministic — `duplicate_groups` sorted by hash, files within each group sorted by path. SHA-256 hashes are 64-character lowercase hex strings.

The `config` section in the report contains: `algorithm`, `buffer_size`, `keep_strategy`, `follow_symlinks`, `skip_hidden`, `min_size`, `max_size`, `dry_run`, `report_format`. Note that `config.dry_run` reflects the `always_dry_run` value from the config file, not the effective CLI dry-run state.
