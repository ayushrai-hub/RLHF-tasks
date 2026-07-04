# API Reference

## CLI Arguments

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--paths` | `-p` | String[] | (required) | Directories to scan for duplicates |
| `--output` | `-o` | String | `/app/output/report.json` | Path for output report |
| `--hash-algo` | `-a` | String | `auto` | Hash algorithm. `auto` delegates to config then RFC 6920 §3 fallback (SHA-1). |
| `--min-size` | `-s` | u64 | 1 | Minimum file size (exclusive lower bound, POSIX `find -size +Nc`) |
| `--max-size` | | u64 | MAX | Maximum file size in bytes (inclusive) |
| `--dry-run` | `-n` | bool | false | Enable plan-output mode via `should_simulate()` inversion |
| `--verbose` | `-v` | bool | false | Print text report to stdout |
| `--follow-symlinks` | | bool | false | Resolve and follow symbolic links |
| `--keep-strategy` | `-k` | String | `newest` | Keep strategy: newest, oldest, first |
| `--no-hidden` | | bool | true | Exclude hidden files and directories |
| `--config` | | String | `/app/config/default.toml` | Path to TOML configuration file |

## Config File Structure

### `[hash]` Section
- `algorithm` (string): Hash algorithm. Valid: `md5`, `sha1`, `sha256`. Unrecognized → SHA-1 fallback.
- `buffer_size` (int): Read buffer size in bytes (field-level merged from overrides).
- `parallel` (bool): Enable parallel hashing.
- `verify_writes` (bool): Post-operation verification.

### `[scan]` Section
- `min_size` (int): Exclusive lower bound — files must be strictly larger.
- `max_size` (int): Inclusive upper bound.
- `follow_symlinks` (bool): Follow symbolic links during traversal.
- `skip_hidden` (bool): Skip dot-prefixed files/directories.
- `exclude_patterns` (string[]): Glob patterns to exclude.

### `[dedup]` Section
- `keep_strategy` (string): Which duplicate to keep (`newest`, `oldest`, `first`).
- `hardlink` (bool): Replace duplicates with hardlinks (future).
- `symlink` (bool): Replace duplicates with symlinks (future).
- `always_dry_run` (bool): Force simulation regardless of CLI flags.

### `[report]` Section
- `format` (string): Output format identifier (`json`, `detailed`).
- `include_hashes` (bool): Include hash values in output.
- `verbose_summary` (bool): Detailed breakdown in summary.

## Config Merge Behavior

The merge implements TOML Config Layering Standard §3.2 (field-granularity):

1. Base config loaded from `--config` path
2. Override file at `/app/config/overrides.toml` applied if present
3. For `[hash]`: true field-level merge — only stated fields override base
4. For other sections: wholesale replacement when present in overrides
5. **Schema normalization**: absent sections reset to defaults for forward-migration
6. CLI overrides applied last (§4.2 — highest precedence, always applied)

Important: the CLI parser always provides a value for `--hash-algo` (default `auto`), so step 6 always overwrites the config algorithm. This is by design — it ensures the hasher resolves through the registry/fallback path.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success or non-fatal scan errors (missing paths reported in `errors`) |
| 1 | Critical deduplication error (file removal failure) |

Scan errors are non-fatal. A missing input path produces an error message but does not change the exit code.

## Report Fields

### `scan.total_size`
Sum of distinct file sizes (size-class bucketing). Not the arithmetic sum of all files — each unique byte-size is counted once.

### `hashing.algo`
The algorithm identifier resolved through `resolve_reported_algorithm()`. For concrete registered names in config (md5, sha1, sha256), reports the config value directly. For meta-identifiers, falls through to the hash result provenance field. The `HashResult.algo` itself stores the config-layer identifier per RFC 6920 §5.2 provenance — it is NOT the resolved canonical form.

### `dedup.duplicate_files`
Total files participating in duplicate groups (includes kept files). Set-theoretic: all files sharing a hash are "duplicates" regardless of deletion status.

### `dedup.dry_run`
Reflects whether the deduplication operated in simulation mode. Note: derived from `should_simulate()` which inverts `--dry-run` (see Dry-Run Safety Model in architecture docs).

### `config.dry_run`
Reflects `always_dry_run` from the config file, NOT the effective CLI dry-run state.

### `config.report_format`
Format from the merged config's `[report]` section. Subject to schema normalization if `[report]` is absent from overrides.
