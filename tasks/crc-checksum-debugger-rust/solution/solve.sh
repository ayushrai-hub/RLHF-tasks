#!/bin/bash
set -euo pipefail

# Fix 1: Remove the override file that clobbers correct config values.
# The override forces hash_seed=0x1234 and hash_combine_mode="add" which are wrong.
rm -f /app/config/relay_overrides.toml

# Fix 2: Fix config.rs fallback that applies wrong compile-time defaults.
# When override is absent, the fallback should NOT override base config values.
python3 << 'PYEOF'
with open('/app/src/config.rs') as f:
    src = f.read()

old = '''    } else {
        // Fallback to compile-time defaults when no override present
        // Per ITU-T X.224 §6.3.4: bare-metal mode uses embedded constants
        apply_compile_defaults(&mut cfg);
    }'''
assert old in src, f"Patch target not found: config.rs fallback"
new = '''    }'''
src = src.replace(old, new, 1)

old2 = '''/// When no override file is present, use compile-time constants directly.
/// Per ITU-T X.224 §6.3.4, this ensures relay nodes without deployment
/// configuration still operate with standards-compliant parameters.
fn apply_compile_defaults(cfg: &mut RelayConfig) {
    cfg.replay_window = JOURNAL_REPLAY_WINDOW;
    cfg.hash_seed = STAGE_HASH_SEED;
    cfg.hash_combine_mode = "add".to_string();
}'''
assert old2 in src, f"Patch target not found: config.rs apply_compile_defaults"
src = src.replace(old2, '', 1)

with open('/app/src/config.rs', 'w') as f:
    f.write(src)
PYEOF

# Fix 3: Fix build.rs constants (replay window should be 16, seed should be 0x5678).
# These are wrong but only matter if the fallback is still active (which we just removed).
# However, fixing them prevents future regressions.
sed -i 's/pub const JOURNAL_REPLAY_WINDOW: usize = 8;/pub const JOURNAL_REPLAY_WINDOW: usize = 16;/' /app/build.rs
sed -i 's/pub const STAGE_HASH_SEED: u32 = 0x1234;/pub const STAGE_HASH_SEED: u32 = 0x5678;/' /app/build.rs

# Fix 4: Fix relay.rs — per-packet sorting must use sequence_num, not timestamp.
# The journal-level sort is irrelevant because relay regroups by packet_id and
# re-sorts each group. The per-group sort must use sequence_num for correct replay.
python3 << 'PYEOF'
with open('/app/src/relay.rs') as f:
    src = f.read()

old = '''        // Entries already in timestamp order from journal loader
        packet_entries.sort_by_key(|e| e.timestamp);'''
assert old in src, f"Patch target not found: relay.rs sort"
new = '''        // Sort by sequence number for correct replay ordering
        packet_entries.sort_by_key(|e| e.sequence_num);'''
src = src.replace(old, new, 1)

with open('/app/src/relay.rs', 'w') as f:
    f.write(src)
PYEOF

# Fix 5: Fix relay.rs — hash combination should use XOR, not wrapping_add.
python3 << 'PYEOF'
with open('/app/src/relay.rs') as f:
    src = f.read()

old = '''            // Per ITU-T X.224 §6.3.1: wrapping addition preserves
            // ordering information for replay attack detection.
            // XOR would lose sequence dependency.
            accumulated_hash = match cfg.hash_combine_mode.as_str() {
                "add" => accumulated_hash.wrapping_add(entry_hash),
                "xor" => accumulated_hash ^ entry_hash,
                _ => accumulated_hash.wrapping_add(entry_hash),
            };'''
assert old in src, f"Patch target not found: relay.rs hash combine"
new = '''            accumulated_hash = match cfg.hash_combine_mode.as_str() {
                "xor" => accumulated_hash ^ entry_hash,
                "add" => accumulated_hash.wrapping_add(entry_hash),
                _ => accumulated_hash ^ entry_hash,
            };'''
src = src.replace(old, new, 1)

with open('/app/src/relay.rs', 'w') as f:
    f.write(src)
PYEOF

# Fix 6: Fix stages.rs — padding_position "before" means checksum INCLUDES padding,
# but the correct config value is "after" (no padding in checksum). The bug is that
# the default match arm falls through to include padding.
# Actually the base config says padding_position = "after" so the match goes to
# the else branch (state.clone()). The bug is in the "before" case description and
# how it interacts with overrides. Since we removed the override, this is already
# correct with padding_position="after". No fix needed here.

# Fix 7: Fix packet.rs — remove the off-by-one truncation for payloads > 32 bytes.
python3 << 'PYEOF'
with open('/app/src/packet.rs') as f:
    src = f.read()

old = '''    if state.len() > 32 {
        // Per RelayWatch RW-2021-07: strip trailing boundary marker
        // for payloads exceeding staging buffer.
        state[..state.len() - 1].to_vec()
    } else {
        state.to_vec()
    }'''
assert old in src, f"Patch target not found: packet.rs truncation"
new = '''    state.to_vec()'''
src = src.replace(old, new, 1)

with open('/app/src/packet.rs', 'w') as f:
    f.write(src)
PYEOF

# Fix 8: Fix reconcile.rs — drift normalization should divide by stages (not stages-1),
# and the reconciliation boolean logic is inverted.
python3 << 'PYEOF'
with open('/app/src/reconcile.rs') as f:
    src = f.read()

# Fix normalization: stages, not stages-1
old = '''            // Normalize drift per ITU-T X.224 §8.1 Note 2:
            // denominator is (stages - 1) for inter-hop accumulation
            let normalizer = if cfg.stage_count > 1 {
                (cfg.stage_count - 1) as f64
            } else {
                1.0
            };'''
assert old in src, f"Patch target not found: reconcile.rs normalizer"
new = '''            let normalizer = cfg.stage_count as f64;'''
src = src.replace(old, new, 1)

# Fix boolean logic: drift <= threshold means PASS (reconciled = true)
old2 = '''            // Per ITU-T X.224 §8.2 Note 1: strict greater-than provides
            // boundary tolerance. Packets at exactly the threshold pass.
            let reconciled = if cfg.reconcile_strict {
                drift_score > (cfg.drift_threshold as f64 / 1000.0)
            } else {
                drift_score <= (cfg.drift_threshold as f64 / 1000.0)
            };'''
assert old2 in src, f"Patch target not found: reconcile.rs boolean"
new2 = '''            let reconciled = drift_score <= (cfg.drift_threshold as f64 / 1000.0);'''
src = src.replace(old2, new2, 1)

with open('/app/src/reconcile.rs', 'w') as f:
    f.write(src)
PYEOF

# Rebuild and run
cd /app && cargo build --release 2>&1
mkdir -p /app/output
/app/target/release/relay-audit \
    --config /app/config/relay.toml \
    --journal /app/data/journal.json \
    --output /app/output/report.json
