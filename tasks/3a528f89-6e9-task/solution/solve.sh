#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN=/app/environment/fixtures/main_a64.elf

readelf -n "$MAIN" 2>/dev/null || true
readelf -d "$MAIN" 2>/dev/null | head -20 || true
cat /app/environment/fixtures/interp_table.toml
cat /app/environment/cfg/profile_routes.toml
cat /app/environment/fixtures/spec_t2/build_a.toml
cat /app/environment/fixtures/spec_t2/build_b.toml

merge=/app/environment/load_r8/merge_r8.c
grep -n 'out_flags' "$merge"
sed -i 's/\*out_flags = (uint32_t)note\[0\];/*out_flags = note[1];/' "$merge"

walk=/app/environment/scan_k3/walk_k3.c
grep -n 'nso' "$walk"
sed -i 's/i + 1 < nso/i < nso/' "$walk"

patch -p0 -d /app < "$ROOT_DIR/patches/link_emit.patch"
patch -p0 -d /app < "$ROOT_DIR/patches/persist_v5.patch"
patch -p0 -d /app < "$ROOT_DIR/patches/harness_core.patch"

make -C /app/environment clean
make -C /app/environment all
/app/tooling/run_h02.sh
