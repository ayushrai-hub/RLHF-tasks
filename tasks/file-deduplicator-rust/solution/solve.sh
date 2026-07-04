#!/bin/bash
set -euo pipefail

# ==================================================================
# Oracle solution for file-deduplicator-rust
# Fixes all bugs across the codebase
# ==================================================================

# --- Fix 1: scanner.rs ---
# Bug A: passes_size_filter uses > (exclusive) instead of >= (inclusive)
# Bug B: aggregate_file_sizes only sums distinct sizes (should sum ALL files)
python3 << 'PYEOF'
with open('/app/src/scanner.rs', 'r') as f:
    src = f.read()

# Fix the size filter: change > to >= for inclusive lower bound
old_filter = '        file_size > min_size && file_size <= max_size'
assert old_filter in src, "scanner.rs: passes_size_filter patch target not found"
src = src.replace(old_filter, '        file_size >= min_size && file_size <= max_size', 1)

# Fix aggregate: sum ALL file sizes (not just distinct size classes)
old_agg = '''    fn aggregate_file_sizes(&self, files: &[FileInfo]) -> u64 {
        let mut size_classes: BTreeMap<u64, u64> = BTreeMap::new();
        for f in files {
            *size_classes.entry(f.size).or_insert(0) += 1;
        }
        // Storage footprint: sum of distinct sizes (shared extents counted once)
        size_classes.keys().copied().sum()
    }'''
assert old_agg in src, "scanner.rs: aggregate_file_sizes patch target not found"
new_agg = '''    fn aggregate_file_sizes(&self, files: &[FileInfo]) -> u64 {
        files.iter().map(|f| f.size).sum()
    }'''
src = src.replace(old_agg, new_agg, 1)

# Remove unused BTreeMap import
src = src.replace('use std::collections::BTreeMap;\n', '', 1)

with open('/app/src/scanner.rs', 'w') as f:
    f.write(src)
print("[OK] scanner.rs patched")
PYEOF

# --- Fix 2: constants.rs ---
# Bug: HASH_FALLBACK_DEFAULT is "sha1" but should be "sha256"
python3 << 'PYEOF'
with open('/app/src/constants.rs', 'r') as f:
    src = f.read()

old = 'pub const HASH_FALLBACK_DEFAULT: &str = "sha1";'
assert old in src, "constants.rs: HASH_FALLBACK_DEFAULT patch target not found"
src = src.replace(old, 'pub const HASH_FALLBACK_DEFAULT: &str = "sha256";', 1)

with open('/app/src/constants.rs', 'w') as f:
    f.write(src)
print("[OK] constants.rs patched")
PYEOF

# --- Fix 3: hasher.rs ---
# Bug A: hash_all stores config algorithm instead of the resolved algorithm in HashResult.algo
# Bug B: find_duplicates uses BTreeMap keyed by size (not hash) for ordering.
python3 << 'PYEOF'
with open('/app/src/hasher.rs', 'r') as f:
    src = f.read()

# Fix A: Store the resolved algo in HashResult, not the config value
old_reported = '''        // The config-layer identifier is preserved for provenance tracking
        // per RFC 6920 §5.2 — consumers of the hash result can verify which
        // configuration produced the hash without re-resolving.
        let reported_algo = self.config.hash.algorithm.clone();

        let results: Vec<HashResult> = files.par_iter().map(|file| {
            let start = Instant::now();
            let hash = self.compute_hash(&file.path, buffer_size, &algo);
            let duration = start.elapsed().as_millis() as u64;

            HashResult {
                path: file.path.clone(),
                hash: hash.unwrap_or_else(|e| format!("ERROR:{}", e)),
                algo: reported_algo.clone(),
                size: file.size,
                duration_ms: duration,
            }
        }).collect();'''
assert old_reported in src, "hasher.rs: reported_algo patch target not found"
new_reported = '''        let results: Vec<HashResult> = files.par_iter().map(|file| {
            let start = Instant::now();
            let hash = self.compute_hash(&file.path, buffer_size, &algo);
            let duration = start.elapsed().as_millis() as u64;

            HashResult {
                path: file.path.clone(),
                hash: hash.unwrap_or_else(|e| format!("ERROR:{}", e)),
                algo: algo.clone(),
                size: file.size,
                duration_ms: duration,
            }
        }).collect();'''
src = src.replace(old_reported, new_reported, 1)

# Fix B: sort final result by hash for true determinism
old_find = '''        ordered.into_values().flatten().collect()'''
assert old_find in src, "hasher.rs: find_duplicates ordering patch target not found"
new_find = '''        let mut result: Vec<DuplicateGroup> = ordered.into_values().flatten().collect();
        result.sort_by(|a, b| a.hash.cmp(&b.hash));
        result'''
src = src.replace(old_find, new_find, 1)

with open('/app/src/hasher.rs', 'w') as f:
    f.write(src)
print("[OK] hasher.rs patched")
PYEOF

# --- Fix 4: config.rs ---
# Bug A: normalize_absent_sections resets [report] (and [scan]) to defaults
#         even though the base config has non-default values (report.format="detailed")
# Bug B: apply_cli_overrides always sets algorithm from CLI (even when "auto")
python3 << 'PYEOF'
with open('/app/src/config.rs', 'r') as f:
    src = f.read()

# Fix A: Remove the schema normalization that resets absent sections
old_norm_call = '''
                // Schema normalization pass: sections absent from overrides
                // are validated against current schema defaults to prevent
                // stale values from persisting across schema migrations.
                self.normalize_absent_sections(&mut result, table);'''
assert old_norm_call in src, "config.rs: normalize call patch target not found"
src = src.replace(old_norm_call, '', 1)

# Fix B: Only override algorithm when CLI value is not "auto"
old_cli = '''        // Algorithm: CLI always takes precedence per §4.2
        self.hash.algorithm = cli.hash_algo.to_lowercase();'''
assert old_cli in src, "config.rs: apply_cli_overrides algo patch target not found"
new_cli = '''        // Algorithm: only override if explicitly specified (not "auto")
        let cli_algo = cli.hash_algo.to_lowercase();
        if cli_algo != "auto" {
            self.hash.algorithm = cli_algo;
        }'''
src = src.replace(old_cli, new_cli, 1)

with open('/app/src/config.rs', 'w') as f:
    f.write(src)
print("[OK] config.rs patched")
PYEOF

# --- Fix 5: report.rs ---
# Bug A: duplicate_files counts ALL files in groups (should subtract one per group)
# Bug B: hashing.algo uses config value instead of resolved algo from hash_results
python3 << 'PYEOF'
with open('/app/src/report.rs', 'r') as f:
    src = f.read()

# Fix A: subtract kept files (one per group) from duplicate count
old_dup = '''        // Duplicate files: total count of files participating in groups
        let total_dup_files: usize = self.duplicate_groups.iter()
            .map(|g| g.files.len())
            .sum();'''
assert old_dup in src, "report.rs: duplicate_files patch target not found"
new_dup = '''        // Duplicate files: redundant copies (total in groups minus one kept per group)
        let total_dup_files: usize = self.duplicate_groups.iter()
            .map(|g| g.files.len().saturating_sub(1))
            .sum();'''
src = src.replace(old_dup, new_dup, 1)

# Fix B: hashing.algo should reflect the actual resolved algorithm
old_algo = '''            // Report the resolved algorithm from hash results (§5.1 provenance)
            algo: self.resolve_reported_algorithm(),'''
assert old_algo in src, "report.rs: hashing.algo patch target not found"
new_algo = '''            // Report the actual resolved algorithm used for hashing
            algo: self.hash_results.first()
                .map(|h| h.algo.clone())
                .unwrap_or_else(|| self.config.hash.algorithm.clone()),'''
src = src.replace(old_algo, new_algo, 1)

with open('/app/src/report.rs', 'w') as f:
    f.write(src)
print("[OK] report.rs patched")
PYEOF

# --- Fix 6: main.rs ---
# Bug A: Uses cli.should_simulate() which inverts dry_run
# Bug B: Exit code only checks dedup errors, not scan errors
python3 << 'PYEOF'
with open('/app/src/main.rs', 'r') as f:
    src = f.read()

# Fix A: Use cli.dry_run directly instead of should_simulate()
old_sim = '    let dedup_result = deduper.deduplicate(&duplicate_groups, cli.should_simulate());'
assert old_sim in src, "main.rs: should_simulate patch target not found"
src = src.replace(old_sim, '    let dedup_result = deduper.deduplicate(&duplicate_groups, cli.dry_run);', 1)

# Fix B: Also exit 1 on scan errors
old_exit = '''    // Exit with non-zero status on critical errors
    let has_critical_errors = dedup_result.errors.is_some()
        && !dedup_result.errors.as_ref().unwrap().is_empty();
    if has_critical_errors {
        std::process::exit(1);
    }'''
assert old_exit in src, "main.rs: exit code patch target not found"
new_exit = '''    // Exit with non-zero status on any errors (scan or dedup)
    let has_scan_errors = !scan_result.errors.is_empty();
    let has_dedup_errors = dedup_result.errors.is_some()
        && !dedup_result.errors.as_ref().unwrap().is_empty();
    if has_scan_errors || has_dedup_errors {
        std::process::exit(1);
    }'''
src = src.replace(old_exit, new_exit, 1)

with open('/app/src/main.rs', 'w') as f:
    f.write(src)
print("[OK] main.rs patched")
PYEOF

# --- Build ---
cd /app && cargo build --release 2>&1

echo ""
echo "=== All patches applied and build successful ==="
