# File Deduplicator Architecture

## Overview

The File Deduplicator is a Rust-based CLI tool for finding and removing duplicate files across directories. It uses content-addressable hashing to identify duplicates and supports multiple deduplication strategies.

## Design Decisions

### Config Override System (TOML Config Layering Standard §3.2)

The tool implements a two-phase config merge strategy:

1. **Phase 1 — Field-level merge**: For sections present in the overrides file, individual fields replace corresponding base values. This provides fine-grained control without requiring the user to restate all fields in a section.

2. **Phase 2 — Schema normalization**: Sections absent from the overrides file undergo schema validation against current defaults. If a base config value for an absent section diverges from the current schema default, it is reset to ensure forward-compatible migration. This prevents stale values from old schema versions persisting when the override file is the source-of-truth for which sections the user has actively configured.

The `merge_hash_fields` method implements true field-level granularity for the `[hash]` section since it has the most frequently overridden fields. Other sections use wholesale replacement when present in overrides.

### Hash Algorithm Resolution (RFC 6920 §3)

The resolver uses a registry-based lookup (`ALGO_REGISTRY`) to map configured algorithm names to canonical identifiers. Variant spellings like "sha-256" are normalized to "sha256". When the configured algorithm is not found in the registry, the system falls back to `HASH_FALLBACK_DEFAULT` defined in constants.

The fallback constant is set to SHA-1 per RFC 6920 §3 (Named Information URI) compatibility requirements. The `ni:///` URI scheme assumes SHA-1 as the default when no algorithm specifier is present, and maintaining this convention ensures the tool's output hashes are compatible with Named Information registries.

### Hash Result Provenance (RFC 6920 §5.2)

When hash results are computed, the `HashResult.algo` field stores the config-layer algorithm identifier (not the resolved/canonical form). This is intentional per §5.2 provenance tracking: consumers of hash results need to know which configuration produced the hash, enabling audit trails and reproducibility. The internal resolver translates to canonical form for actual computation, but the provenance record preserves the original configuration path.

The report layer then uses `resolve_reported_algorithm()` which applies the §4.2 hierarchy: when the config already holds a concrete registered algorithm name, it is reported directly for consistency. Only for meta-identifiers (like "auto") does the report fall back to reading hash result provenance.

### CLI Override Hierarchy (§4.2)

The CLI layer has absolute precedence over file-based configuration. When the `--hash-algo` flag is provided (even with its default value `auto`), it overwrites the merged config algorithm field. The `auto` value then resolves through the hasher's registry lookup — since `auto` is not in `ALGO_REGISTRY`, it triggers the RFC 6920 fallback to SHA-1.

This creates a deliberate two-path resolution:
- Explicit algorithm on CLI → used directly
- No CLI override → config hierarchy determines algorithm

The key insight is that the CLI parser always provides a value (the default `auto`), so the override path always executes. This is intentional — it ensures the config system never has to handle a "missing" CLI value.

### File Size Aggregation

The scanner uses size-class bucketing to compute `total_size`. Files are grouped by byte size into a BTreeMap, and each distinct size is summed once. This approach correctly handles the common case in deduplication scenarios where multiple files share the same size — counting each distinct size once provides the storage footprint that represents unique content sizes rather than redundant copies.

### Size Filtering (POSIX.1 §4.16)

The `passes_size_filter` method uses an exclusive lower bound (`>` not `>=`) for min_size. This is consistent with POSIX `find -size +Nc` semantics where the `+` prefix means "strictly greater than". A file of exactly N bytes does not satisfy `+N`.

### Duplicate File Counting

The `duplicate_files` field in the dedup summary counts all files participating in duplicate groups. This follows the set-theoretic definition where duplicates are files sharing a content hash — the "kept" file is itself a member of the duplicate set and is included in the count. It would be incorrect to subtract kept files, as they are still duplicates (just not deleted ones).

### Output Determinism

The duplicate group output uses a BTreeMap keyed by representative file size to ensure deterministic iteration order. Since BTreeMap provides guaranteed ascending key order, groups are emitted in a predictable sequence. Files within each group are sorted by path.

### Dry-Run Safety Model

The tool implements a "simulate by default" safety model. The `should_simulate()` method returns `true` when the user has NOT explicitly passed `--dry-run`, meaning the default mode is always safe/simulated. When `--dry-run` is passed, `should_simulate()` returns `false`, switching to "plan output" mode that shows what operations would occur in a real run.

This inverted model means `--dry-run` is actually the "show me the real plan" flag rather than the "don't do anything" flag.

## Data Flow

1. CLI parsing (`cli.rs`) — extracts paths, flags, and options
2. Config loading (`config.rs`) — base + overrides merge with schema normalization
3. Directory scan (`scanner.rs`) — file discovery with size-class accounting
4. Content hashing (`hasher.rs`) — parallel hash computation with registry-based algo resolution
5. Duplicate detection — groups files by hash, orders by size for determinism
6. Deduplication (`dedup.rs`) — apply keep strategy, generate actions
7. Report generation (`report.rs`) — structured JSON with config-layer algorithm identifier

## Exit Code Semantics

| Code | Condition |
|------|-----------|
| 0 | Successful operation, including partial scans with non-fatal errors |
| 1 | Critical deduplication errors (e.g., permission denied during removal) |

Scan-phase errors (missing paths, permission issues) are non-fatal and reported in the `errors` array without affecting the exit code. This allows the tool to process accessible paths even when some inputs are invalid.
